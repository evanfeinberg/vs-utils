#!/usr/bin/env python
"""
Featurize molecules and save features to disk. Featurizers are exposed as
subcommands, with __init__ arguments as subcommand arguments.
"""

__author__ = "Steven Kearnes"
__copyright__ = "Copyright 2014, Stanford University"
__license__ = "BSD 3-clause"

import argparse
import inspect
import joblib
import numpy as np
import pandas as pd

from vs_utils.features import get_featurizers
from vs_utils.utils import (read_pickle, ScaffoldGenerator, SmilesGenerator,
                            write_dataframe)
from vs_utils.utils.parallel_utils import LocalCluster
from vs_utils.utils.rdkit_utils import serial


def parse_args(input_args=None):
    """
    Parse command-line arguments. Each featurizer class is a subcommand
    whose arguments are stored in args.featurizer_kwargs. The featurizer
    class is stored in args.klass.

    Parameters
    ----------
    input_args : list, optional
        Input arguments. If not provided, defaults to sys.argv[1:].
    """
    parser = argparse.ArgumentParser(formatter_class=HelpFormatter)
    parser.add_argument('input',
                        help='Input molecules.')
    parser.add_argument('--chiral-scaffolds', action='store_true',
                        help='Whether to include chirality in scaffolds.')
    parser.add_argument('-t', '--targets',
                        help='Molecule targets.')
    parser.add_argument('--smiles-hydrogens', action='store_true')
    parser.add_argument('--scaffolds', action='store_true',
                        help='Calculate molecule scaffolds.')
    parser.add_argument('--smiles', action='store_true', dest='include_smiles',
                        help='Include molecule SMILES.')
    parser.add_argument('-p', '--parallel', action='store_true',
                        help='Whether to use IPython.parallel.')
    parser.add_argument('-id', '--cluster-id',
                        help='IPython.parallel cluster ID.')
    parser.add_argument('-np', '--n-engines', type=int,
                        help='Start a local IPython.parallel cluster with ' +
                             'this many engines.')
    parser.add_argument('output',
                        help=('Output filename (.joblib, .pkl, .pkl.gz, .csv, '
                              'or .csv.gz).'))
    parser.add_argument('-c', '--compression-level', type=int, default=3,
                        help='Compression level (0-9) to use with ' +
                             'joblib.dump.')
    parser.add_argument('--mol-prefix',
                        help='Prefix for molecule IDs.')

    # featurizer subcommands
    featurizers = get_featurizers()
    subparsers = parser.add_subparsers(title='featurizers')
    for name, klass in featurizers.items():
        command = subparsers.add_parser(name, help=klass.__doc__,
                                        formatter_class=HelpFormatter,
                                        epilog=klass.__doc__)
        command.set_defaults(klass=klass)
        try:
            args, _, _, defaults = inspect.getargspec(klass.__init__)
        except TypeError:
            args = []
        for i, arg in enumerate(args):
            if i == 0 and arg == 'self':
                continue
            kwargs = {}
            try:
                kwargs['default'] = defaults[i - len(args)]
                if kwargs['default'] is not None:
                    kwargs['type'] = type(kwargs['default'])
            except IndexError:
                kwargs['required'] = True
            if 'type' in kwargs and kwargs['type'] == bool:
                if kwargs['default']:
                    command.add_argument('--no-{}'.format(arg), dest=arg,
                                         action='store_false')
                else:
                    command.add_argument('--{}'.format(arg),
                                         action='store_true')
            else:
                command.add_argument('--{}'.format(arg), **kwargs)
    args = argparse.Namespace()
    args.featurizer_kwargs = parser.parse_args(input_args)
    for arg in ['input', 'output', 'klass', 'targets', 'parallel',
                'cluster_id', 'n_engines', 'compression_level',
                'smiles_hydrogens', 'include_smiles', 'scaffolds',
                'chiral_scaffolds', 'mol_prefix']:
        setattr(args, arg, getattr(args.featurizer_kwargs, arg))
        delattr(args.featurizer_kwargs, arg)
    return args


class HelpFormatter(argparse.RawTextHelpFormatter):
    """
    Argparse help formatter with better indenting.

    Parameters
    ----------
    WRITEME
    """
    def __init__(self, prog, indent_increment=2, max_help_position=8,
                 width=None):
        super(HelpFormatter, self).__init__(prog, indent_increment,
                                            max_help_position, width)


def main(featurizer_class, input_filename, output_filename,
         target_filename=None, featurizer_kwargs=None, parallel=False,
         client_kwargs=None, view_flags=None, compression_level=3,
         smiles_hydrogens=False, include_smiles=False, scaffolds=False,
         chiral_scaffolds=False, mol_id_prefix=None):
    """
    Featurize molecules in input_filename using the given featurizer.

    Parameters
    ----------
    featurizer_class : Featurizer
        Featurizer class.
    input_filename : str
        Filename containing molecules to be featurized.
    output_filename : str
        Output filename. Should end with .pkl or .pkl.gz.
    target_filename : str, optional
        Pickle containing target values. Should either be array_like or a dict
        containing 'names' and 'y' keys, corresponding to molecule names and
        target values.
    featurizer_kwargs : dict, optional
        Keyword arguments passed to featurizer.
    parallel : bool, optional
        Whether to train subtrainers in parallel using IPython.parallel
        (default False).
    client_kwargs : dict, optional
        Keyword arguments for IPython.parallel Client.
    view_flags : dict, optional
        Flags for IPython.parallel LoadBalancedView.
    compression_level : int, optional (default 3)
        Compression level (0-9) to use with joblib.dump.
    smiles_hydrogens : bool, optional (default False)
        Whether to keep hydrogens when generating SMILES.
    include_smiles : bool, optional (default False)
        Include SMILES in output.
    scaffolds : bool, optional (default False)
        Whether to include scaffolds in output.
    chiral_scaffods : bool, optional (default False)
        Whether to include chirality in scaffolds.
    mol_id_prefix : str, optional
        Prefix for molecule IDs.
    """
    mols, mol_ids = read_mols(input_filename, mol_id_prefix=mol_id_prefix)

    # get targets
    data = {}
    if target_filename is not None:
        targets = read_pickle(target_filename)
        if isinstance(targets, dict):
            mol_indices, target_indices = collate_mols(
                mols, mol_ids, targets['y'], targets['mol_id'])
            mols = mols[mol_indices]
            mol_ids = mol_ids[mol_indices]
            targets = np.asarray(targets['y'])[target_indices]
        else:
            assert len(targets) == len(mols)
        data['y'] = targets

    # featurize molecules
    print "Featurizing molecules..."
    if featurizer_kwargs is None:
        featurizer_kwargs = {}
    featurizer = featurizer_class(**featurizer_kwargs)
    features = featurizer.featurize(mols, parallel, client_kwargs, view_flags)

    # fill in data container
    print "Saving results..."
    data['mol_id'] = mol_ids
    data['features'] = features

    # sanity checks
    assert data['features'].shape[0] == len(mols), (
        "Features do not match molecules.")
    assert data['mol_id'].shape[0] == len(mols), (
        "Molecule IDs do not match molecules.")

    # smiles, scaffolds, args
    if include_smiles:
        smiles = SmilesGenerator(remove_hydrogens=(not smiles_hydrogens))
        data['smiles'] = np.asarray([smiles.get_smiles(mol) for mol in mols])
    if scaffolds:
        data['scaffolds'] = get_scaffolds(mols, chiral_scaffolds)

    # construct a DataFrame
    try:
        if data['features'].ndim > 1:
            # numpy arrays will be "summarized" when written as strings
            # use str(row.tolist())[1:-1] to remove the surrounding brackets
            # remove commas (keeping spaces) to avoid conflicts with csv
            if (output_filename.endswith('.csv')
                    or output_filename.endswith('.csv.gz')):
                data['features'] = [str(row.tolist())[1:-1].replace(', ', ' ')
                                    for row in data['features']]
            else:
                data['features'] = [row for row in data['features']]
    except AttributeError:
        pass
    df = pd.DataFrame(data)

    # write output file
    write_output_file(df, output_filename, compression_level)


def collate_mols(mols, mol_names, targets, target_ids):
    """
    Prune and reorder mols to match targets.

    Parameters
    ----------
    mols : array_like
        Molecules.
    mol_names : array_like
        Molecule names.
    targets : array_like
        Targets.
    target_ids : array_like
        Molecule IDs corresponding to targets.

    Returns
    -------
    which_mols : array_like
        Indices of molecules to keep, ordered to match targets.
    keep_targets : array_like
        Targets corresponding to selected molecules. This could differ from
        the input targets if some of the targets do not have a corresponding
        molecule (this often happens when a 3D structure cannot be generated
        for a molecule that has target data).
    """
    print "Collating molecules and targets..."
    assert len(mols) == len(mol_names) and len(targets) == len(target_ids)

    # make sure dtypes match for names so comparisons will work properly
    target_names = np.asarray(target_ids)
    mol_names = np.asarray(mol_names).astype(target_names.dtype)

    # sanity checks
    if np.unique(mol_names).size != mol_names.size:
        raise ValueError('Molecule names must be unique.')
    if np.unique(target_names).size != target_names.size:
        raise ValueError('Molecule names (for targets) must be unique.')

    # get intersection of mol_names and target_names
    shared_names = np.intersect1d(mol_names, target_names)

    # get indices to select those molecules from mols and targets
    mol_indices = np.zeros_like(shared_names, dtype=int)
    target_indices = np.zeros_like(shared_names, dtype=int)
    for i, name in enumerate(shared_names):
        mol_indices[i] = np.where(mol_names == name)[0][0]
        target_indices[i] = np.where(target_names == name)[0][0]
    return mol_indices, target_indices


def read_mols(input_filename, mol_id_prefix=None, log_every_N=1000):
    """
    Read molecules from an input file and extract names.

    Parameters
    ----------
    input_filename : str
      Filename containing molecules.
    log_every_N: int
      Print log statement every N molecules read.
    """
    print "Reading molecules..."
    mols = []
    names = []
    with serial.MolReader().open(input_filename) as reader:
      for num, mol in enumerate(reader.get_mols()):
        if num % 1000 == 0:
          print "Reading molecule %d" % num
        mols.append(mol)
        if mol.HasProp('_Name'):
          name = mol.GetProp('_Name')
          if mol_id_prefix is not None:
            name = mol_id_prefix + name
          names.append(name)
        else:
          names.append(None)
    mols = np.asarray(mols)
    names = np.asarray(names)
    return mols, names


def get_scaffolds(mols, include_chirality=False):
    """
    Get Murcko scaffolds for molecules.

    Murcko scaffolds are described in DOI: 10.1021/jm9602928. They are
    essentially that part of the molecule consisting of rings and the linker
    atoms between them.

    Parameters
    ----------
    mols : array_like
        Molecules.
    include_chirality : bool, optional (default False)
        Whether to include chirality in scaffolds.
    """
    print "Generating molecule scaffolds..."
    engine = ScaffoldGenerator(include_chirality=include_chirality)
    scaffolds = []
    for mol in mols:
        scaffolds.append(engine.get_scaffold(mol))
    scaffolds = np.asarray(scaffolds)
    return scaffolds


def write_output_file(data, filename, compression_level=3):
    """
    Pickle output data, possibly to a compressed file.

    Parameters
    ----------
    data : object
        Object to pickle in output file.
    filename : str
        Output filename. Should end with .joblib, .pkl, or .pkl.gz.
    compression_level : int, optional (default 3)
        Compression level (0-9) to use with joblib.dump.
    """
    if filename.endswith('.joblib'):
      joblib.dump(data, filename, compress=compression_level)
    else:
      write_dataframe(data, filename)

if __name__ == '__main__':
    args = parse_args()

    # start a cluster
    if args.n_engines is not None:
        assert args.cluster_id is None, ('Cluster ID should not be should ' +
                                         'not be specified when starting a' +
                                         'new cluster.')
        cluster = LocalCluster(args.n_engines)
        args.parallel = True
        args.cluster_id = cluster.cluster_id

    # cluster flags
    if args.cluster_id is not None:
        client_kwargs = {'cluster_id': args.cluster_id}
    else:
        client_kwargs = None
    view_flags = {'retries': 1}

    # run main function
    main(featurizer_class=args.klass,
         input_filename=args.input,
         output_filename=args.output,
         target_filename=args.targets,
         featurizer_kwargs=vars(args.featurizer_kwargs),
         parallel=args.parallel,
         client_kwargs=client_kwargs,
         view_flags=view_flags,
         compression_level=args.compression_level,
         smiles_hydrogens=args.smiles_hydrogens,
         include_smiles=args.include_smiles,
         scaffolds=args.scaffolds,
         chiral_scaffolds=args.chiral_scaffolds,
         mol_id_prefix=args.mol_prefix)

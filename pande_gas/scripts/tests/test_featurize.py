"""
Test featurize.py.
"""
import cPickle
import gzip
import joblib
import numpy as np
from rdkit_utils import conformers, serial
import shutil
import tempfile
import unittest

from rdkit import Chem
from rdkit.Chem import AllChem

from pande_gas.scripts.featurize import main, parse_args


class TestFeaturize(unittest.TestCase):
    """
    Test featurize.py.
    """
    def setUp(self):
        """
        Set up for tests. Writes molecules and targets to files.
        """
        self.temp_dir = tempfile.mkdtemp()
        smiles = ['CC(=O)OC1=CC=CC=C1C(=O)O', 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O']
        self.names = ['aspirin', 'ibuprofen']
        engine = conformers.ConformerGenerator(max_conformers=1)
        self.mols = []
        for i in xrange(len(smiles)):
            mol = Chem.MolFromSmiles(smiles[i])
            mol.SetProp('_Name', self.names[i])
            self.mols.append(engine.generate_conformers(mol))

        # write mols
        _, self.input_filename = tempfile.mkstemp(suffix='.sdf',
                                                  dir=self.temp_dir)
        writer = serial.MolWriter()
        writer.open(self.input_filename)
        writer.write(self.mols)
        writer.close()

        # write targets
        self.targets = [0, 1]
        _, self.targets_filename = tempfile.mkstemp(suffix='.pkl',
                                                    dir=self.temp_dir)
        with open(self.targets_filename, 'wb') as f:
            cPickle.dump(self.targets, f, cPickle.HIGHEST_PROTOCOL)

    def tearDown(self):
        """
        Delete temporary files.

        Parameters
        ----------
        filenames : list
            Filenames to delete.
        """
        shutil.rmtree(self.temp_dir)

    def check_output(self, featurize_args, shape, targets=None, names=None,
                     output_suffix='.pkl'):
        """
        Check features shape, targets, and names.

        Parameters
        ----------
        featurize_args : list
            Featurizer-specific arguments for script.
        filename : str
            Output filename.
        shape : tuple
            Expected shape of features.
        targets : list, optional
            Expected targets. Defaults to self.targets.
        names : list, optional
            Expected names. Defaults to self.names.
        output_suffix : str, optional (default '.pkl')
            Suffix for output files.
        """

        # generate command-line arguments
        _, output_filename = tempfile.mkstemp(suffix=output_suffix,
                                              dir=self.temp_dir)
        input_args = [self.input_filename, '-t', self.targets_filename,
                      output_filename] + featurize_args

        # run script
        args = parse_args(input_args)
        main(args.klass, args.input, args.output, args.targets,
             vars(args.featurizer_kwargs),
             chiral_scaffolds=args.chiral_scaffolds)

        # read output file
        if output_filename.endswith('.joblib'):
            data = joblib.load(output_filename)
        elif output_filename.endswith('.gz'):
            with gzip.open(output_filename) as f:
                data = cPickle.load(f)
        else:
            with open(output_filename) as f:
                data = cPickle.load(f)

        # check values
        if targets is None:
            targets = self.targets
        if names is None:
            names = self.names
        assert data['features'].shape == shape, data['features'].shape
        assert np.array_equal(data['y'], targets), data['y']
        assert np.array_equal(data['names'], names), data['names']

        # return output in case anything else needs to be checked
        return data

    def test_pickle(self):
        """
        Save features to a pickle.
        """
        self.check_output(['circular'], (2, 2048))

    def test_compressed_pickle(self):
        """
        Save features to a compressed pickle.
        """
        self.check_output(['circular'], (2, 2048), output_suffix='.pkl.gz')

    def test_joblib(self):
        """
        Save features using joblib.dump.
        """
        self.check_output(['circular'], (2, 2048), output_suffix='.joblib')

    def test_circular(self):
        """
        Test circular fingerprints.
        """
        self.check_output(['circular', '--size', '512'], (2, 512))

    def test_coulomb_matrix(self):
        """
        Test Coulomb matrices.
        """
        self.check_output(['coulomb_matrix', '--max_atoms', '50'],
                          (2, 1, 1275))

    def test_image_features(self):
        """
        Test image features.
        """
        self.check_output(['image', '--size', '16'], (2, 16, 16, 3))

    def test_esp(self):
        """
        Test ESP.
        """
        self.check_output(['esp', '--size', '20'], (2, 1, 61, 61, 61))

    def test_shape_grid(self):
        """
        Test ShapeGrid.
        """
        self.check_output(['shape', '--size', '40'], (2, 1, 40, 40, 40))

    def test_mw(self):
        """
        Test calculation of molecular weight.
        """
        self.check_output(['mw'], (2, 1))

    def test_descriptors(self):
        """
        Test calculation of RDKit descriptors.
        """
        self.check_output(['descriptors'], (2, 196))

    def test_scaffolds(self):
        """
        Test scaffold generation.
        """
        data = self.check_output(['circular'], (2, 2048))
        assert Chem.MolFromSmiles(data['scaffolds'][0]).GetNumAtoms() == 6
        assert Chem.MolFromSmiles(data['scaffolds'][1]).GetNumAtoms() == 6

    def test_chiral_scaffolds(self):
        """
        Test chiral scaffold generation.
        """

        # romosetron
        mol = Chem.MolFromSmiles(
            'CN1C=C(C2=CC=CC=C21)C(=O)[C@@H]3CCC4=C(C3)NC=N4')
        AllChem.Compute2DCoords(mol)
        self.mols[1] = mol

        # write mols
        _, self.input_filename = tempfile.mkstemp(suffix='.sdf',
                                                  dir=self.temp_dir)
        writer = serial.MolWriter()
        writer.open(self.input_filename)
        writer.write(self.mols)
        writer.close()

        # run script w/o chiral scaffolds
        data = self.check_output(['circular'], (2, 2048))
        achiral_scaffold = data['scaffolds'][1]

        # run script w/ chiral scaffolds
        data = self.check_output(['--chiral-scaffolds', 'circular'], (2, 2048))
        chiral_scaffold = data['scaffolds'][1]

        assert achiral_scaffold != chiral_scaffold

    def test_collate_mols1(self):
        """
        Test collate_mols where molecules are pruned.
        """

        # write targets
        targets = {'names': ['ibuprofen'], 'y': [0]}
        with open(self.targets_filename, 'wb') as f:
            cPickle.dump(targets, f, cPickle.HIGHEST_PROTOCOL)

        # run script
        self.check_output(['circular'], (1, 2048), targets=targets['y'],
                          names=targets['names'])

    def test_collate_mols2(self):
        """
        Test collate_mols where targets are pruned.
        """

        # write targets
        targets = {'names': ['aspirin', 'ibuprofen'], 'y': [0, 1]}
        with open(self.targets_filename, 'wb') as f:
            cPickle.dump(targets, f, cPickle.HIGHEST_PROTOCOL)

        # write mols
        writer = serial.MolWriter()
        writer.open(self.input_filename)
        writer.write([self.mols[0]])
        writer.close()

        # run script
        self.check_output(['circular'], (1, 2048), targets=[0],
                          names=['aspirin'])

    def test_collate_mols3(self):
        """
        Test collate_mols where targets are in a different order than
        molecules.
        """

        # write targets
        targets = {'names': ['ibuprofen', 'aspirin'], 'y': [1, 0]}
        with open(self.targets_filename, 'wb') as f:
            cPickle.dump(targets, f, cPickle.HIGHEST_PROTOCOL)

        # run script
        self.check_output(['circular'], (2, 2048), targets=[0, 1],
                          names=['aspirin', 'ibuprofen'])

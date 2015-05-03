"""
Test NNScore Helper Classes

Most of the PDB data files for ligands where generated by obabel from the
corresponding pubchem entries. The receptor PDBs (prgr) are taken from the
DUD-E dataset.
"""
import os
import tempfile
import shutil
import unittest
import numpy as np

from vs_utils.features.nnscore_helper import Point
from vs_utils.features.nnscore_helper import Atom
from vs_utils.features.nnscore_helper import PDB
from vs_utils.features.nnscore_helper import average_point
from vs_utils.features.tests import __file__ as test_directory


def data_dir():
  """Get location of data directory."""
  return os.path.join(os.path.dirname(test_directory), "data")


class TestPoint(unittest.TestCase):
  """
  Test point class.
  """
  def setUp(self):
    """
    Instantiate local points for tests.
    """
    self.point_a = Point(1,2,3)
    self.point_b = Point(-1,-2,-3)

  def testCopyOf(self):
    """
    TestPoint: Verify that copy_of copies x,y,z correctly.
    """
    copy_point = self.point_a.copy_of()
    assert copy_point.x == 1
    assert copy_point.y == 2
    assert copy_point.z == 3

  def testAveragePoint(self):
    avg_point = average_point(self.point_a, self.point_b)
    assert avg_point.x == 0
    assert avg_point.y == 0
    assert avg_point.z == 0

  def testDistTo(self):
    """
    TestPoint: Verify that dist_to implements L2-distance.
    """
    ## || point_a - point_b ||_2 = ||(1,2,3) - (-1,-2,-3)||_2
    ##                           = ||(2,4,6)||_2
    ##                           = sqrt(4 + 16 + 36)
    ##                           = sqrt(56)
    assert self.point_a.dist_to(self.point_b) == np.sqrt(56)

  def testMagnitude(self):
    """
    TestPoint: Verify that magnitude implements L2-Norm.
    """
    ## || (1, 2, 3) ||_2 = || (-1, -2, -3) ||_2
    ##                   = sqrt(1 + 4 + 9)
    ##                   = sqrt(14)
    assert self.point_a.magnitude() == np.sqrt(14)
    assert self.point_b.magnitude() == np.sqrt(14)

class TestAtom(unittest.TestCase):
  """
  Test atom class.
  """

  def setUp(self):
    """
    Instantiates a pair of atom objects for tests.
    """
    self.empty_atom = Atom()
    self.trial_atom = Atom()
    self.trial_atom.atomname = "C"
    self.trial_atom.coordinates = Point(1,2,3)
    self.trial_atom.charge = 0.
    self.trial_atom.element = "C"
    self.trial_atom.residue = "CYS"
    # TODO(bramsundar): Fill in a non-junk value for chain.
    self.trial_atom.chain = "FF"
    self.trial_atom.indices_of_atoms_connecting = [4, 5, 6]

  def testCopyOf(self):
    """
    TestAtom: Verify that copy_of preserves atom information.
    """
    copy_atom = self.trial_atom.copy_of()
    assert copy_atom.atomname == "C"
    assert copy_atom.coordinates.x == 1
    assert copy_atom.coordinates.y == 2
    assert copy_atom.coordinates.z == 3
    assert copy_atom.charge == 0
    assert copy_atom.element == "C"
    assert copy_atom.residue == "CYS"
    assert copy_atom.chain == "FF"
    assert copy_atom.indices_of_atoms_connecting == [4, 5, 6]

  def testCreatePDBLine(self):
    """
    TestAtom: Verify that PDB Line is in correct format.
    """
    # TODO(bramsundar): Add a more nontrivial test after looking into
    # PDB standard.
    line = self.trial_atom.create_PDB_line(1)
    assert type(line) == str

  def testNumberOfNeighors(self):
    """
    TestAtom: Verify that the number of neighbors is computed correctly.
    """
    assert self.empty_atom.number_of_neighbors() == 0
    assert self.trial_atom.number_of_neighbors() == 3

class TestPDB(unittest.TestCase):
  """"
  Test PDB class.
  """

  def setUp(self):
    """
    Instantiate a dummy PDB file.
    """
    self.temp_dir = tempfile.mkdtemp()
    self.pdb = PDB()

    _, self.pdb_filename = tempfile.mkstemp(suffix=".pdb",
        dir=self.temp_dir)


  def tearDown(self):
    """
    Delete temporary directory.
    """
    shutil.rmtree(self.temp_dir)

  def testSaveAndLoad(self):
    """
    TestPDB: Saves dummy PDB to file and verifies that it can be reloaded.
    """
    self.pdb.save_PDB(self.pdb_filename)
    empty_pdb = PDB()
    with open(self.pdb_filename) as pdb_file:
      for line in pdb_file:
        print line
    empty_pdb.load_PDB_from_file(self.pdb_filename)

  def testAddNewAtom(self):
    """
    TestPDB: Verifies that new atoms can be added.
    """
    # Verify that no atoms are present when we start.
    assert len(self.pdb.all_atoms.keys()) == 0
    empty_atom = Atom()
    self.pdb.add_new_atom(empty_atom)
    # Verify that we now have one atom
    assert len(self.pdb.all_atoms.keys()) == 1

  def testAssignProteinCharges(self):
    """
    TestPDB: Assigns charges to residues.
    """
    # TODO(rbharath): This test is just a stub. Break out unit tests for
    # each of the specific residues to actually get meaningful coverage
    # here.
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)

  def testGetResidues(self):
    """
    TestPDB: Tests that all residues in PDB are identified.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    residues = prgr_pdb.get_residues()
    # prgr.pdb has 280 unique residues
    assert len(residues) == 280
    prgr_residues = ["LEU", "ILE", "ASN", "LEU", "LEU", "MET", "SER",
        "ILE", "GLU", "PRO", "ASP", "VAL", "ILE", "TYR", "ALA", "GLY", "HIS",
        "ASP", "THR", "SER", "SER", "SER", "LEU", "LEU", "THR", "SER", "LEU",
        "ASN", "GLN", "LEU", "GLY", "GLU", "ARG", "GLN", "LEU", "LEU", "SER",
        "VAL", "VAL", "LYS", "TRP", "SER", "LYS", "SER", "LEU", "PRO", "GLY",
        "PHE", "ARG", "LEU", "HIS", "ILE", "ASP", "ASP", "GLN", "ILE", "THR",
        "LEU", "ILE", "GLN", "TYR", "SER", "TRP", "MET", "SER", "LEU", "MET",
        "VAL", "PHE", "GLY", "LEU", "GLY", "TRP", "ARG", "SER", "TYR", "LYS",
        "HIS", "VAL", "SER", "GLY", "GLN", "MET", "LEU", "TYR", "PHE", "ALA",
        "PRO", "ASP", "LEU", "ILE", "LEU", "ASN", "GLU", "GLN", "ARG", "MET",
        "LYS", "GLU", "PHE", "TYR", "SER", "LEU", "CYS", "LEU", "THR", "MET",
        "TRP", "GLN", "ILE", "PRO", "GLN", "GLU", "PHE", "VAL", "LYS", "LEU",
        "GLN", "VAL", "SER", "GLN", "GLU", "GLU", "PHE", "LEU", "CYS", "MET",
        "LYS", "VAL", "LEU", "LEU", "LEU", "LEU", "ASN", "THR", "ILE", "PRO",
        "LEU", "GLU", "GLY", "LEU", "PHE", "MET", "ARG", "TYR", "ILE", "GLU",
        "LEU", "ALA", "ILE", "ARG", "ARG", "PHE", "TYR", "GLN", "LEU", "THR",
        "LYS", "LEU", "LEU", "ASP", "ASN", "LEU", "HIS", "ASP", "LEU", "VAL",
        "LYS", "GLN", "LEU", "HIS", "LEU", "TYR", "CYS", "LEU", "ASN", "THR",
        "PHE", "ILE", "GLN", "SER", "ARG", "ALA", "LEU", "SER", "VAL", "GLU",
        "PHE", "PRO", "GLU", "MET", "MET", "SER", "GLU", "VAL", "ILE", "ALA",
        "ALA", "GLN", "LEU", "PRO", "LYS", "ILE", "LEU", "ALA", "GLY", "MET",
        "VAL", "LYS", "PRO", "LEU", "LEU", "PHE", "HIS", "LYS", "ASN", "LEU",
        "ASP", "ASP", "ILE", "THR", "LEU", "ILE", "GLN", "TYR", "SER", "TRP",
        "MET", "THR", "ILE", "PRO", "LEU", "GLU", "GLY", "LEU", "ARG", "VAL",
        "LYS", "GLN", "LEU", "HIS", "LEU", "TYR", "CYS", "LEU", "ASN", "THR",
        "PHE", "ILE", "GLN", "SER", "ARG", "ALA", "LEU", "SER", "VAL", "GLU",
        "PHE", "PRO", "GLU", "MET", "MET", "SER", "GLU", "VAL", "ILE", "ALA",
        "ALA", "GLN", "LEU", "PRO", "LYS", "ILE", "LEU", "ALA", "GLY", "MET",
        "VAL", "LYS", "PRO"]
    # Recall the keys have format RESNAME_RESNUMBER_CHAIN
    resnames = [reskey.split("_")[0].strip() for (reskey, _) in residues]
    assert resnames == prgr_residues
    # prgr.pdb has 2749 unique atoms.
    atom_count = 0
    for (_, atom_indices) in residues:
      atom_count += len(atom_indices)
    assert atom_count == 2749

  def testGetLysineCharges(self):
    """
    TestPDB: Test that lysine charges are identified correctly.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    lysine_charges = prgr_pdb.get_lysine_charges(res_list)
    # prgr has 14 lysines.
    assert len(lysine_charges) == 14
    for charge in lysine_charges:
      # Lysine should be posistively charged
      assert charge.positive

  def testGetArginineCharges(self):
    """
    TestPDB: Test that arginine charges are identified correctly.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    arginine_charges = prgr_pdb.get_arginine_charges(res_list)
    # prgr has 10 arginines
    assert len(arginine_charges) == 10
    for charge in arginine_charges:
      # The guanidium in arginine should be positively charged.
      assert charge.positive

  def testGetHistidineCharges(self):
    """
    TestPDB: Test that histidine charges are identified correctly.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    histidine_charges = prgr_pdb.get_histidine_charges(res_list)
    # prgr has 7 arginines
    assert len(histidine_charges) == 7
    for charge in histidine_charges:
      # The nitrogens pick up positive charges
      assert charge.positive

  def testGetGlutamicAcidCharges(self):
    """
    TestPDB: Test that glutamic acid charges are identified correctly.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    glutamic_acid_charges = prgr_pdb.get_glutamic_acid_charges(res_list)
    print len(glutamic_acid_charges)
    assert len(glutamic_acid_charges) == 16
    for charge in glutamic_acid_charges:
      # The carboxyls get deprotonated.
      assert not charge.positive

  def testGetAsparticAcidCharges(self):
    """
    TestPDB: Test that aspartic acid charges are identified correctly.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    aspartic_acid_charges = prgr_pdb.get_aspartic_acid_charges(res_list)
    assert len(aspartic_acid_charges) == 9
    for charge in aspartic_acid_charges:
      # The carboxyls get deprotonated
      assert not charge.positive

  def testGetPhenylalanineAromatics(res_list):
    """
    TestPDB: Test that phenylalanine aromatic rings are retrieved.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    phenylalanine_aromatics = prgr_pdb.get_phenylalanine_aromatics(res_list)
    # prgr has 13 phenylalanines, each of which has 1 aromatic ring.
    assert len(phenylalanine_aromatics) == 13
    for aromatic in phenylalanine_aromatics:
      # The aromatic rings in phenylalanine have 6 elements each
      assert len(aromatic.indices) == 6

  def testGetTyrosineAromatics(res_list):
    """
    TestPDB: Test that tyrosine aromatic rings are retrieved.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    tyrosine_aromatics = prgr_pdb.get_tyrosine_aromatics(res_list)
    # prgr has 10 tyrosines, each of which has 1 aromatic ring.
    assert len(tyrosine_aromatics) == 10
    for aromatic in tyrosine_aromatics:
      # The aromatic rings in tyrosine have 6 elements each
      assert len(aromatic.indices) == 6

  def testGetHistidineAromatics(res_list):
    """
    TestPDB: Test that histidine aromatic rings are retrieved.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    histidine_aromatics = prgr_pdb.get_histidine_aromatics(res_list)
    # prgr has 7 histidines, each of which has 1 aromatic ring.
    assert len(histidine_aromatics) == 7
    for aromatic in histidine_aromatics:
      # The aromatic rings in histidine have 6 elements each
      print len(aromatic.indices)
      assert len(aromatic.indices) == 5

  def testGetTryptophanAromatics(res_list):
    """
    TestPDB: Test that tryptophan aromatic rings are retrieved.
    """
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    
    res_list = prgr_pdb.get_residues()
    print "About to get tryptophan_aromatics!"
    tryptophan_aromatics = prgr_pdb.get_tryptophan_aromatics(res_list)
    # prgr has 5 tryptophans, each of which has 2 aromatic ring.
    print len(tryptophan_aromatics)
    assert len(tryptophan_aromatics) == 10 
    num_five_rings, num_six_rings = 0, 0
    for aromatic in tryptophan_aromatics:
      # One aromatic ring in tryptophan hahas 6 elements each,
      # while the other has 5 elements.
      if len(aromatic.indices) == 6:
        num_six_rings += 1
      elif len(aromatic.indices) == 5:
        num_five_rings += 1
    assert num_six_rings == 5
    assert num_five_rings == 5

  def testConnectedAtomsOfGivenElement(self):
    """
    TestPDB: Verifies that connected atom retrieval works.
    """
    # Verify that no atoms are present when we start.
    assert len(self.pdb.all_atoms.keys()) == 0
    carbon_atom = Atom(element="C")
    oxygen_atom = Atom(element="O")
    hydrogen_atom = Atom(element="H")

    self.pdb.add_new_atom(carbon_atom)
    self.pdb.add_new_atom(oxygen_atom)
    self.pdb.add_new_atom(hydrogen_atom)

    # We want a carboxyl, so C connects O and H
    carbon_atom.indices_of_atoms_connecting = [2,3]
    oxygen_atom.indices_of_atoms_connecting = [1]
    hydrogen_atom.indices_of_atoms_connecting = [1]

    connected_oxygens = self.pdb.connected_atoms_of_given_element(1, "O")
    assert len(connected_oxygens) == 1

    connected_hydrogens = self.pdb.connected_atoms_of_given_element(1, "H")
    assert len(connected_hydrogens) == 1

  def testLoadBondsFromPDBList(self):
    """
    TestPDB: Verifies that bonds can be loaded from PDB.
    """
    # Test that we can load CO2
    carbon_atom = Atom(element="C")
    oxygen_atom_1 = Atom(element="O")
    oxygen_atom_2 = Atom(element="O")

    self.pdb.add_new_atom(carbon_atom)
    self.pdb.add_new_atom(oxygen_atom_1)
    self.pdb.add_new_atom(oxygen_atom_2)
    lines = [
      "CONECT    1    2    3                                                 "
      "CONECT    2                                                           "
      "CONECT    3                                                           "
    ]
    self.pdb.load_bonds_from_PDB_list(lines)
    assert len(carbon_atom.indices_of_atoms_connecting) == 2
    assert len(oxygen_atom_1.indices_of_atoms_connecting) == 0
    assert len(oxygen_atom_2.indices_of_atoms_connecting) == 0


  def testConnectedHeavyAtoms(self):
    """
    TestPDB: Verifies retrieval of connected heavy atoms.
    """
    # Verify that no atoms are present when we start.
    assert len(self.pdb.all_atoms.keys()) == 0
    carbon_atom = Atom(element="C")
    oxygen_atom = Atom(element="O")
    hydrogen_atom = Atom(element="H")

    self.pdb.add_new_atom(carbon_atom)
    self.pdb.add_new_atom(oxygen_atom)
    self.pdb.add_new_atom(hydrogen_atom)

    # We want a carboxyl, so C connects O and H
    carbon_atom.indices_of_atoms_connecting = [2,3]
    oxygen_atom.indices_of_atoms_connecting = [1]
    hydrogen_atom.indices_of_atoms_connecting = [1]

    connected_heavy_atoms = self.pdb.connected_heavy_atoms(1)
    assert len(connected_heavy_atoms) == 1
    assert connected_heavy_atoms[0] == 2

  def testCreateNonProteinAtomBondsByDistance(self):
    """
    TestPDB: Verifies creation of bonds.
    """
    # First test a toy example
    carbon_atom = Atom(element="C", coordinates=Point(0,0,1))
    oxygen_atom = Atom(element="O", coordinates=Point(0,0,2))

    self.pdb.add_new_non_protein_atom(carbon_atom)
    self.pdb.add_new_non_protein_atom(oxygen_atom)

    self.pdb.create_non_protein_atom_bonds_by_distance()
    assert len(carbon_atom.indices_of_atoms_connecting) == 1
    assert len(oxygen_atom.indices_of_atoms_connecting) == 1

  def testAssignNonProteinCharges(self):
    """
    TestPDB: Verify that charges are properly added to ligands.
    """
    # Test ammonium sulfate: (NH4)+(NH4)+(SO4)(2-)
    # There should be 3 charged groups, two positive, one negative
    ammonium_sulfate_pdb = PDB()
    ammonium_sulfate_pdb_path = os.path.join(data_dir(),
        "ammonium_sulfate.pdb")
    # Notice that load automatically identifies non-protein charges.
    ammonium_sulfate_pdb.load_PDB_from_file(
        ammonium_sulfate_pdb_path)
    assert len(ammonium_sulfate_pdb.charges) == 3
    num_pos, num_neg = 0, 0
    for charge in ammonium_sulfate_pdb.charges:
      if charge.positive:
        num_pos += 1
      else:
        num_neg += 1
    assert num_pos == 2
    assert num_neg == 1

  def testIdentifyMetallicCharges(self):
    """
    TestPDB: Verify that non-protein charges are assigned properly.
    """
    # Test metallic ion charge.
    magnesium_pdb = PDB()
    magnesium_atom = Atom(element="MG", coordinates=Point(0,0,0))
    magnesium_pdb.add_new_non_protein_atom(magnesium_atom)
    metallic_charges = magnesium_pdb.identify_metallic_charges()
    assert len(metallic_charges) == 1

  def testIdentifyNitrogenGroupCharges(self):
    """
    TestPDB: Verify that nitrogen groups are charged correctly.
    """
    # Test ammonium sulfate: (NH4)+(NH4)+(SO4)(2-)
    # The labeling should pick up 2 charged nitrogen groups for two
    # ammoniums.
    ammonium_sulfate_pdb = PDB()
    ammonium_sulfate_pdb_path = os.path.join(data_dir(),
        "ammonium_sulfate.pdb")
    ammonium_sulfate_pdb.load_PDB_from_file(
        ammonium_sulfate_pdb_path)
    nitrogen_charges = ammonium_sulfate_pdb.identify_nitrogen_group_charges()
    assert len(nitrogen_charges) == 2
    assert nitrogen_charges[0].positive  # Should be positive
    assert nitrogen_charges[1].positive  # Should be positive

    # Test pyrrolidine (CH2)4NH. The nitrogen here should be sp3
    # hybridized, so is likely to pick up an extra proton to its nitrogen
    # at physiological pH.
    pyrrolidine_pdb = PDB()
    pyrrolidine_pdb_path = os.path.join(data_dir(),
        "pyrrolidine.pdb")
    pyrrolidine_pdb.load_PDB_from_file(pyrrolidine_pdb_path)
    nitrogen_charges = pyrrolidine_pdb.identify_nitrogen_group_charges()
    assert len(nitrogen_charges) == 1
    assert nitrogen_charges[0].positive  # Should be positive

  def testIdentifyCarbonGroupCharges(self):
    """
    TestPDB: Verify that carbon groups are charged correctly.
    """
    # Guanidine is positively charged at physiological pH
    guanidine_pdb = PDB()
    guanidine_pdb_path = os.path.join(data_dir(),
        "guanidine.pdb")
    guanidine_pdb.load_PDB_from_file(
        guanidine_pdb_path)
    carbon_charges = guanidine_pdb.identify_carbon_group_charges()
    assert len(carbon_charges) == 1
    assert carbon_charges[0].positive  # Should be positive

    # sulfaguanidine contains a guanidine group that is likely to be
    # positively protonated at physiological pH
    sulfaguanidine_pdb = PDB()
    sulfaguanidine_pdb_path = os.path.join(data_dir(),
        "sulfaguanidine.pdb")
    sulfaguanidine_pdb.load_PDB_from_file(
        sulfaguanidine_pdb_path)
    carbon_charges = sulfaguanidine_pdb.identify_carbon_group_charges()
    assert len(carbon_charges) == 1
    assert carbon_charges[0].positive  # Should be positive

    # Formic acid is a carboxylic acid, which
    formic_acid_pdb = PDB()
    formic_acid_pdb_path = os.path.join(data_dir(),
        "formic_acid.pdb")
    formic_acid_pdb.load_PDB_from_file(
        formic_acid_pdb_path)
    carbon_charges = formic_acid_pdb.identify_carbon_group_charges()
    assert len(carbon_charges) == 1
    assert not carbon_charges[0].positive  # Should be negatively charged.

  def testIdentifyPhosphorusGroupCharges(self):
    """
    TestPDB: Verify that Phosphorus groups are charged correctly.
    """
    # CID82671 contains a phosphate between two aromatic groups.
    phosphate_pdb = PDB()
    phosphate_pdb_path = os.path.join(data_dir(),
      "82671.pdb")
    phosphate_pdb.load_PDB_from_file(
        phosphate_pdb_path)
    phosphorus_charges = phosphate_pdb.identify_phosphorus_group_charges()
    assert len(phosphorus_charges) == 1
    assert not phosphorus_charges[0].positive  # Should be negatively charged.


  def testIdentifySulfurGroupCharges(self):
    """
    TestPDB: Verify that sulfur groups are charged correctly.
    """
    trifluoromethanesulfonic_acid_pdb = PDB()
    trifluoromethanesulfonic_acid_pdb_path = os.path.join(data_dir(),
      "trifluoromethanesulfonic_acid.pdb")
    trifluoromethanesulfonic_acid_pdb.load_PDB_from_file(
      trifluoromethanesulfonic_acid_pdb_path)
    sulfur_charges = (
        trifluoromethanesulfonic_acid_pdb.identify_sulfur_group_charges())
    assert len(sulfur_charges) == 1
    assert not sulfur_charges[0].positive  # Should be negatively charged.


  def testLigandAssignAromaticRings(self):
    """
    TestPDB: Verify that aromatic rings in ligands are identified.
    """
    benzene_pdb = PDB()
    benzene_pdb_path = os.path.join(data_dir(), "benzene.pdb")
    benzene_pdb.load_PDB_from_file(benzene_pdb_path)

    # A benzene should have exactly one aromatic ring.
    assert len(benzene_pdb.aromatic_rings) == 1
    # The first 6 atoms in the benzene pdb form the aromatic ring.
    assert (set(benzene_pdb.aromatic_rings[0].indices)
         == set([1,2,3,4,5,6]))

  def testAssignSecondaryStructure(self):
    """
    TestPDB: Verify that secondary structure is assigned meaningfully.
    """
    # TODO(rbharath): This test is just a stub. Add a more realistic test
    # that checks that nontrivial secondary structure is computed correctly
    # here.
    prgr_pdb = PDB()
    prgr_pdb_path = os.path.join(data_dir(), "prgr.pdb")
    prgr_pdb.load_PDB_from_file(prgr_pdb_path)
    prgr_pdb.assign_secondary_structure()
    

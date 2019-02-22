"""Mass Equality Set Graph (MESGraph)."""

from SBMLLint.common import constants as cn
from SBMLLint.common.molecule import Molecule, MoleculeStoichiometry
from SBMLLint.common.reaction import Reaction
from SBMLLint.games.som import SOM
from SBMLLint.common.simple_sbml import SimpleSBML

import itertools
import networkx as nx

REACTION = "reaction"
LESSTHAN = "<"

class MESGraph(nx.DiGraph):
  """
  The MESGraph class represents a collection of SOMs as nodes
  and their inequality relationships as edges (arcs).
  Mass inequality between SOMs from reactions can help us
  detect their relationship.
  Type I Error occurs when we find inequality between two molecules
  in the same SOM, because each element in a SOM has the same weight.
  Type II Error implies there is cyclism between molecules, such as
  A < B < C < ... < A, which is physically impossible.
  """

  def __init__(self, simple=None):
    """
    :param list-SOM soms:
    """
    super(MESGraph, self).__init__()
    self.soms = self.initializeSOMs(simple)
    self.add_nodes_from(self.soms)
    self.identifier = self.makeId()

  def __repr__(self):
    return self.identifier

  def initializeSOMs(self, simple):
    """
    Create a list of one-molecule SOMs
    :param SimpleSBML simple:
    :return list-SOM:
    """
    soms = []
    for molecule in simple.molecules:
      soms.append(SOM({molecule}))
    return soms

  def makeId(self):
    """
    Construct an identifier for the graph.
    :return str:
    """
    identifier = ""
    if self.edges:
      for edge in self.edges:
        identifier = identifier + str(edge[0]) + cn.ARC_ARROW + str(edge[1]) + "\n"
    for key, node in enumerate(nx.isolates(self)):
      identifier = identifier + str(node)
      if key < (len(list(nx.isolates(self)))-1):
          identifier = identifier + cn.KINETICS_SEPARATOR
    # Return the identifier
    return identifier

  def getNode(self, molecule):
    """
    Find a node(SOM) containing the given molecule.
    If no such SOM exists, return False
    :param Molecule molecule:
    :return SOM/False:
    """
    for som in list(self.nodes):
      for mole in som.molecules:
        if mole.name == molecule.name:
          return som
    return False

  def processUniUniReaction(self, reaction):
    """
    Process a 1-1 reaction to merge nodes.
    If no need to merge, return None.
    :param Reaction reactions:
    """
    if reaction.category != cn.REACTION_1_1:
      pass
    else:
      reactant_som = self.getNode(reaction.reactants[0].molecule)
      product_som = self.getNode(reaction.products[0].molecule)
      if reactant_som == product_som:
        return None
      else:
        new_som = reactant_som.merge(product_som)
        new_som.reactions.add(reaction)
        # TODO: if there are edges, need to also check them
        self.remove_node(reactant_som)
        self.remove_node(product_som)
        self.add_node(new_som)
        self.identifier = self.makeId()
        return new_som

  def processUniMultiReaction(self, reaction):
    """
    Process a 1-n reaction to add arcs.
    Since the mass of reactant is greater than
    that of each product, it adds arcs by
    addArc(source=products, destination=reactant).
    :param Reaction reaction:
    """
    if reaction.category != cn.REACTION_1_n:
      pass
    else:
      destination = [reaction.reactants[0].molecule]
      source = [product.molecule for product in reaction.products]
      self.addArc(source, destination, reaction)
      self.identifier = self.makeId()

  def processMultiUniReaction(self, reaction):
    """
    Process a n-1 reaction to add arcs.
    Since the mass of product is greater than
    that of each reactant, it adds arcs by
    addArc(source=reactants, destination=product).
    :param Reaction reaction:
    """
    if reaction.category != cn.REACTION_n_1:
      pass
    else:
      destination = [reaction.products[0].molecule]
      source = [reactant.molecule for reactant in reaction.reactants]
      self.addArc(source, destination, reaction)
      self.identifier = self.makeId()

  def addArc(self, source, destination, reaction=None):
    """
    Add arcs (edges) using two molecule lists (source/destination).
    :param list-Molecule source:
    :param list-Molecule destination:
    """
    arcs = itertools.product(source, destination)
    for arc in arcs:
      if not self.checkTypeOneError(arc, reaction):
        arc_source = self.getNode(arc[0])
        arc_destination = self.getNode(arc[1])
        # if there is already a preious reaction,
        if self.has_edge(arc_source, arc_destination):
          reaction_label = self.get_edge_data(arc_source, arc_destination)[REACTION]
          # if reaction.label is not already included in the attribute,
          if reaction.label not in set(reaction_label):
            reaction_label = reaction_label + [reaction.label]
        else:
          reaction_label = [reaction.label]
        self.add_edge(arc_source, arc_destination, reaction=reaction_label)
      else:
        continue

  def checkTypeOneError(self, arc, inequality_reaction=None):
    """
    Check Type I Error of an arc.
    If both source and destination are found
    in the same SOM, send error message and return True.
    If not, return False.
    :param tuple-Molecule arc:
    :param Reaction inequality_reaction:
    :return bool:
    """
    som1 = self.getNode(arc[0])
    som2 = self.getNode(arc[1])
    if som1 == som2:
      print("We have Type I Error...")
      print(arc[0], " and ", arc[1], " have the same weight by")
      for equality_reaction in list(som1.reactions):
        print(equality_reaction)
      print("\nHowever, reaction \"", inequality_reaction, 
            "\" implies ", arc[0], LESSTHAN, arc[1])
      print()
      return True
    else:
      return False

  def analyze(self, reactions):
    """
    Sort list of reactions and process them.
    Add arcs or sending error messages using
    checkTypeOneError or checkTypeTwoError.
    :param list-Reaction reactions:
    """
    # Associate the reaction category with the function
    # that processes that category
    reaction_dic = {
        cn.REACTION_1_1: self.processUniUniReaction,
        cn.REACTION_1_n: self.processUniMultiReaction,
        cn.REACTION_n_1: self.processMultiUniReaction,
        }
    # Process each type of reaction
    for category in reaction_dic.keys():
      for reaction in [r for r in reactions if r.category == category]:
        func = reaction_dic[category]
        func(reaction)
    #
    return self

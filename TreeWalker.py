
class TreeWalker:
    """ Walks the node tree rooted at given node """
    def __init__(self, node, get_children = lambda node: node.all_children(0), cycle_func = lambda node, parent: None):
        self.root_node    = node
        self.get_children = get_children
        self.cycle_func   = cycle_func
        self.reset()

    def reset(self):
        """ Re-start the tree walk, beginning with the root node passed to the constructor. """
        children = self.get_children(self.root_node) if self.root_node else [ ]

        if children:
            self.node_stack   = [ children[:] ]
            self.parent_stack = [ self.root_node ]
        else:
            self.node_stack   = [ ]
            self.parent_stack = [ ]

        self.history      = [ ]

    def is_done(self):
        """ Check if all child nodes have been traversed. """
        return not self.node_stack

    def __nonzero__(self):
        """ Check if there are still child nodes to be traversed. """
        return not not self.node_stack

    def next_child(self):
        """
            Return the next child node, together in a tuple with its immediate parent, from the node tree rooted at the initial
            root node. Child nodes are traversed in depth order, but parents are enumerated before their children.

            The root node itself is not returned; it will appear as the immediate parent in the tuple for the first child node,
            if any.

            A history of previously returned nodes is kept internally and consulted for each new node to be returned, to prevent
            an infinite loop when traversing a dependency cycle.

            Returns (None, None) after all children have been traversed, or if there are no children in the given root node.
        """
        if self.node_stack:
            parent = self.parent_stack[-1]
            node   = self.node_stack[-1].pop(0)

            if not self.node_stack[-1]:
                self.node_stack.pop()
                self.parent_stack.pop()

            if node not in self.history:
                self.history.append(node)

                children = self.get_children(node)

                if children:
                    self.node_stack.append(children[:])
                    self.parent_stack.append(node)

                return node, parent
            else:
                self.cycle_func(node, parent)
                return self.next_child()

        return None, None


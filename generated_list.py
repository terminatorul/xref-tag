
class generated_list(list):
    """
        List class populated with elements using the given generator.

        The generator will be invoked whenever the list is iterated, searched or counted.

        Because of this property the class can be used as an optimization to wrap a generator as a
        'built-in list', in specific cases when you need both:
            - an object that successfully type-checks as a build-in list, ex. isinstance(obj, list)
            - you need to iterate only one element at a time, so the expanded list is never needed

        A simple use case is when the list is used only once or so, and you want to delay evaluation of
        the generator until that time.

        Any direct element access (lst[i]), list slices with negative or reverse-order bounds, list
        concatenation or multiplication and any list modification will internally populate a python
        built-in list with values return by the generator. Afterwards the object behaves like a python
        built-in list, and the generator is forgotten.
    """

    def __init__(self, gen_fn, *gen_args):
        super(generated_list, self).__init__()
        self.gen_fn = gen_fn
        self.gen_args = gen_args
        self.nonzero = None

    def Expand(self):
        """
            Request populating the internal python built-in list with the elements returned by the
            generator. Use this in advance if you want to avoid repeated calls of the generator and use
            the extra memory for a real list instead. The generator function will be forgotten after the
            call.
        """
        if self.gen_fn:
            super(generated_list, self).extend([ x for x in self.gen_fn(*self.gen_args) ])
            self.gen_fn = None
            self.gen_args = None

    def _sequence_comparation(self, other, cmp_fn):
        if self.gen_fn:
            other_it = None
            other_x = None
            try:
                other_it = other.__iter__()
            except AttributeError:
                Expand()
                return cmp_fn(self, other)

            for x in self.gen_fn(*self.gen_args):
                try:
                    other_x = other_it.next()
                except StopIteration:
                    return cmp_fn(1, 0)

                result = cmp_fn(x, other_x)

                if result:
                    return result

            try:
                other_x = other_it.next()
                return cmp_fn(0, 1)
            except StopIteration:
                return cmp_fn(0, 0)
        else:
            return cmp_fn(self, other)

    def __cmp__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: -1 if l < r else (1 if l > r else 0))
        else:
            if hasattr(list, '__cmp__'):
                return super(self, '__cmp__')(other)
            else:
                if super(self, '__lt__')(other):
                    return -1
                else:
                    if super(self, '__gt__')(other):
                        return 1
                    else:
                        return 0

    def __lt__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: l < r)
        else:
            if hasattr(list, '__lt__'):
                return super(generated_list, self).__lt__(other)
            else:
                return super(generated_list, self).__cmp__(other) < 0

    def __le__(self, other):
        if self.gen_fn:
            return self.__cmp__(other) <= 0
        else:
            if hasattr(list, '__le__'):
                return super(generated_list, self).__le__(other)
            else:
                return super(generated_list, self).__cmp__(other) <= 0

    def __eq__(self, other):
        if self.gen_fn:
            return not self._sequence_comparation(other, lambda l, r: not l == r)
        else:
            if hasattr(list, '__eq__'):
                return super(generated_list, self).__eq__(other)
            else:
                return not super(generated_list, self).__cmp__(other)

    def __ne__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: l != r)
        else:
            if hasattr(list, '__ne__'):
                return super(generated_list, self).__ne__(other)
            else:
                return not not super(generated_list, self).__cmp__(other)

    def __gt__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: l > r)
        else:
            if hasattr(list, '__gt__'):
                return super(generated_list, self).__gt__(other)
            else:
                return super(generated_list, self).__cmp__(other) > 0

    def __ge__(self, other):
        if self.gen_fn:
            return self.__cmp__(other) >= 0
        else:
            if hasattr(list, '__ge__'):
                return super(generated_list, self).__ge__(other)
            else:
                return super(generated_list, self).__cmp__(other) >= 0

    def __repr__(self):
        if self.gen_fn:
            return \
                "source_browse_base.generated_list(" \
                    + \
                ', '.join([ repr(x) for x in [ self.gen_fn ] + list(self.gen_args) ]) \
                    + \
                ')'
        else:
            return super(generated_list, self).__repr__()

    def __str__(self):
        if self.gen_fn:
            return '[' + ', '.join([ str(x) for x in self.gen_fn(*self.gen_args) ]) + ']'
        else:
            return super(generator_list, self).__str__()

    def __nonzero__(self):
        if self.gen_fn:
            if self.nonzero is None:
                for x in self.gen_fn(*self.gen_args):
                    self.nonzero = True
                    break

                if not self.nonzero:
                    self.nonzero = False

            return self.nonzero
        else:
            if hasattr(list, '__nonzero__'):
                return super(generated_list, self).__nonzero__()
            else:
                return not not super(generated_list, self).__len__()

    def index(self, val, min_index = None, max_index = None):
        if self.gen_fn and (min_index is None or min_index >= 0) and (max_index is None or max_index >= min_index):
            if min_index is None:
                min_index = 0

            idx = 0
            for x in self.gen_fn(*self.gen_args):
                if idx < min_index:
                    idx += 1
                    continue
                else:
                    if max_index is not None and idx > max_index:
                        break

                if val == x:
                    return idx

                idx += 1

            return -1
        else:
            return super(generated_list, self).index(val)

    def count(self, val):
        if self.gen_fn:
            count = 0

            for x in self.gen_fn(*self.gen_args):
                if val == x:
                    count += 1

            return count
        else:
            return super(generated_list, self).count(val)

    def __len__(self):
        if self.gen_fn:
            length = 0

            for x in self.gen_fn(*self.gen_args):
                length += 1

            return length
        else:
            return super(generated_list, self).__len__()

    def __getitem__(self, pos):
        if \
                self.gen_fn \
                    and \
                isinstance(pos, slice) \
                    and \
                (pos.start is None or pos.start >= 0) \
                    and \
                (pos.stop is None or pos.stop >= pos.start):
            start  = pos.start
            step   = pos.step
            stop   = pos.stop
            idx    = 0
            result = [ ]

            if start is None:
                start = 0

            if step is None or step == 0:
                step = 1

            else:
                if step < 0:
                    step = -step

            for x in self.gen_fn(*self.gen_args):
                if idx < start:
                    idx += 1
                    continue

                if idx > stop:
                    break

                if (idx - start) % step == 0:
                    result.append(x)

                idx += 1

            return result
        else:
            self.Expand()
            return super(generated_list, self).__getitem__(pos)

    def __setitem__(self, pos, val):
        self.Expand()
        return super(generated_list, self).__setitem__(pos, val)

    def __delitem__(self, pos):
        self.Expand()
        return super(generated_lsit, self).__delitem__(pos)

    def __iter__(self):
        if self.gen_fn:
            return self.gen_fn(*self.gen_args)
        else:
            return super(generated_list, self).__iter__()

    def __reversed__(self):
        self.Expand()
        return super(generated_list, self).__reversed__(self)

    def __contains__(self, val):
        if self.gen_fn:
            return self.index(val) >= 0
        else:
            super(generated_list, self).__contains__(val)

    def __getslice__(self, start_pos, end_pos):
        if self.gen_fn and (start_pos is None or start_pos >= 0) and (end_pos is None or end_pos >= 0):
            idx = 0
            result = [ ]

            if start_pos is None:
                start_pos = 0

            for x in self.gen_fn(*self.gen_args):
                if idx < start_pos:
                    idx += 1
                    continue

                if end_pos is not None and idx > end_pos:
                    break;

                result.append(x)
                idx += 1

            if end_pos is not None and idx <= end_pos:
                raise IndexError("List index out of range")

            return result
        else:
            self.Expand()
            return super(generated_list, self).__getslice__(start_pos, end_pos)

    def __setslice__(self, start_pos, end_pos, val):
        self.Expand()
        return super(generated_list, self).__setslice__(start_pos, end_pos, val)

    def __delslice__(self, start_pos, end_pos):
        self.Expand()
        return super(generated_list, self).__delslice__(start_pos, end_pos)

    def __add__(self, other):
        self.Expand()
        return super(generated_list, self).__add__(other)

    def __radd__(self, other):
        self.Expand()
        return super(generated_list, self).__radd__(other)

    def __iadd__(self, other):
        self.Expand()
        return super(generated_list, self).__iadd__(other)

    def __mul__(self, other):
        self.Expand()
        return super(generated_list, self).__mul__(other)

    def __rmul__(self, other):
        self.Expand()
        return super(generated_list, self).__rmul__(other)

    def __imul__(self, other):
        self.Expand()
        return super(generated_list, self).__imul__(other)

    def append(self, val):
        self.Expand()
        return super(generated_list, self).append(val)

    def extend(self, val):
        self.Expand()
        return super(generated_list, self).extend(val)

    def insert(self, pos, val):
        self.Expand()
        return super(generated_list, self).insert(pos, val)

    def pop(self, pos = None):
        self.Expand()

        if pos is None:
            return super(generated_list.self).pop()
        else:
            return super(generated_list.self).pop(pos)

    def remove(self, val):
        self.Expand()
        super(generated_list, self).remove(val)

    def reverse(self):
        self.Expand()
        super(generated_list, self).reverse()

    def sort(self, comp = None, key = None, reverse = False):
        self.Expand()
        if reverse == False:
            if key is None:
                if comp is None:
                    super(generated_list, self).sort()
                else:
                    super(generated_list, self).sort(comp)
            else:
                super(generated_list, self).sort(comp, key)
        else:
            super(generated_list, self).sort(comp, key, reverse)

def test_get_generated_list(env, start_pos = 10, upper_bound = 20):
    def print_generator(start, stop):
        for val in range(start, stop):
                print("Generating value " + str(val))
                yield "val_" + str(val)

    return generated_list(print_generator, start_pos, upper_bound)


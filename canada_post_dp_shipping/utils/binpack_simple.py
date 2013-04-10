#!/usr/bin/env python
# encoding: utf-8
"""
binpack_simple.py

This code implemnts 3D bin packing in pure Python

Bin packing in this context is calculating the best way to store a number of differently sized boxes in a
number of fixed sized "bins". It is what usually happens in a Warehouse bevore shipping.

The Algorithm has a simple fit first approach, but can archive relative good results because it tries
different rectangular rotations of the packages. Since the Algorithm can't interate over all possible
combinations we use a heuristic approach.

For a few dozen packages it reaches adaequate runtime. Below are the results calculated about a set of
500 real world packing problems.

Binsize     Runtime                 Recuction in shipped Packages
600x400x400 31.5993559361 4970 2033 40.9054325956
600x445x400 31.5596890450 4970 1854 37.3038229376
600x500x400 29.1432909966 4970 1685 33.9034205231


On the datasets we operate on we can archive comparable preformance to academic higly optimized C code
like David Pisinger's 3bpp:

     Runtime                 Recuction in shipped Packages
py   11.3468761444 2721 1066 39.1767732451
3bpp 9.95857691765 2721 1086 39.9117971334

The Python implementation is somewhat slower but can archive slightly better packing results on our
datasets.


Created by Maximillian Dornseif on 2010-08-14.
Copyright (c) 2010 HUDORA. All rights reserved.
"""


import time
from itertools import permutations


from package import Package



def packstrip(bin, p):
    """Creates a Strip which fits into bin.

    Returns the Packages to be used in the strip, the dimensions of the strip as a 3-tuple
    and a list of "left over" packages.
    """
    # This code is somewhat optimized and somewhat unreadable
    s = []                # strip
    r = []                # rest
    ss = sw = sl = 0      # stripsize
    bs = bin.heigth       # binsize
    sapp = s.append       # speedup
    rapp = r.append       # speedup
    ppop = p.pop          # speedup
    while p and (ss <= bs):
        n = ppop(0)
        nh, nw, nl = n.size
        if ss + nh <= bs:
            ss += nh
            sapp(n)
            if nw > sw:
                sw = nw
            if nl > sl:
                sl = nl
        else:
            rapp(n)
    return s, (ss, sw, sl), r + p


def packlayer(bin, packages):
    strips = []
    layersize = 0
    layerx = 0
    layery = 0
    binsize = bin.width
    while packages:
        strip, (sizex, stripsize, sizez), rest = packstrip(bin, packages)
        if layersize + stripsize <= binsize:
            packages = rest
            if not strip:
                # we were not able to pack anything
                break
            layersize += stripsize
            layerx = max([sizex, layerx])
            layery = max([sizez, layery])
            strips.extend(strip)
        else:
            # Next Layer please
            packages = strip + rest
            break
    return strips, (layerx, layersize, layery), packages


def packbin(bin, packages):
    packages.sort(reverse=True)
    layers = []
    contentheigth = 0
    contentx = 0
    contenty = 0
    binsize = bin.length
    while packages:
        layer, (sizex, sizey, layersize), rest = packlayer(bin, packages)
        if contentheigth + layersize <= binsize:
            packages = rest
            if not layer:
                # we were not able to pack anything
                break
            contentheigth += layersize
            contentx = max([contentx, sizex])
            contenty = max([contenty, sizey])
            layers.extend(layer)
        else:
            # Next Bin please
            packages = layer + rest
            break
    return layers, (contentx, contenty, contentheigth), packages


def packit(bin, originalpackages):
    packedbins = []
    packages = sorted(originalpackages, reverse=True)
    rest = packages
    while packages:
        packagesinbin, (binx, biny, binz), rest = packbin(bin, packages)
        if not packagesinbin:
            # we were not able to pack anything
            break
        packedbins.append(packagesinbin)
        packages = rest
    # we now have a result, try to get a better result by rotating some bins

    return packedbins, rest


class Timeout(Exception):
    pass


def allpermutations_helper(permuted, todo, maxcounter, callback, bin, bestpack, counter):
    if not todo:
        return counter + callback(bin, permuted, bestpack)
    else:
        others = todo[1:]
        thispackage = todo[0]
        for dimensions in set(permutations((thispackage[0], thispackage[1], thispackage[2]))):
            thispackage = Package(dimensions,
                                  weight=thispackage.weight,
                                  description=thispackage.description,
                                  nosort=True)
            if thispackage in bin:
                counter = allpermutations_helper(permuted + [thispackage], others, maxcounter, callback,
                                                 bin, bestpack, counter)
            if counter > maxcounter:
                raise Timeout('more than %d iterations tries' % counter)
        return counter


def trypack(bin, packages, bestpack):
    bins, rest = packit(bin, packages)
    if len(bins) < bestpack['bincount']:
        bestpack['bincount'] = len(bins)
        bestpack['bins'] = bins
        bestpack['rest'] = rest
    if bestpack['bincount'] < 2:
        raise Timeout('optimal solution found')
    return len(packages)


def allpermutations(todo, bin, iterlimit=5000):
    bestpack = dict(bincount=len(todo) + 1)
    try:
        # First try unpermuted
        trypack(bin, todo, bestpack)
        # now try permutations
        allpermutations_helper([], todo, iterlimit, trypack, bin, bestpack, 0)
    except Timeout, e:
        pass
    return bestpack['bins'], bestpack['rest']

def packing_cost(packs, bin):
    """
    We will define the cost of a packing schema as the empty space in the boxes
    """
    dif = sum(bin.volume - sum(p.volume for p in pack) for pack in packs)
    return bin.girth + dif + (1000 if bin[0] > 100 else 0)

def sort_bins(bins, packages):
    """
    sorts the bins according to how many of the packages can each accomodate
    and filters out the ones that cannot fit any
    """
    each = {}
    for bin in bins:
        each[bin] = 0
        for package in packages:
            if package in bin:
                each[bin] += 1
    def bincmp(s, ot):
        c = cmp(each[s], each[ot])
        return c or cmp(s.girth, ot.girth)
    bins = filter(lambda x: each[x] != 0, bins)
    bins.sort(cmp=bincmp, reverse=True)
    return bins

def iterate_permutations(original_packages, bins, iterlimit):
    """Should not be used from without the library

    Iterates through single-sized bin package algorithms to return an
    approximation to the best fit.
    """
    if not bins:
        return [], original_packages
    if not original_packages:
        return original_packages, []
    costs = []
    packlist = []
    packages = sorted(original_packages, reverse=True)
    bins = sort_bins(bins, packages)
    if not bins:
        return [], original_packages

    for ix, bin in enumerate(bins):
        packs, rest = allpermutations(packages, bin, iterlimit)

        cost = packing_cost(packs, bin)
        newpacks = []

        if rest:
            restpacks, rest = iterate_permutations(rest, bins[ix+1:], iterlimit)
            if rest:
                continue
            cost += sum(packing_cost(p, b) for p, b in restpacks)
            newpacks.extend(restpacks)

        # the cost is the sum of every bigger bin's packaging cost without the
        #  last box (since it was passed on the following
        if ix > 0:
            cost += sum(packing_cost(ps, b) for ps, b in packlist[ix-1][:-1])
            for ps, b in packlist[ix-1][:-1]:
                newpacks.append((ps, b))

            ps, b = packlist[ix-1][-1]
            if ps[:-1]:
                cost += packing_cost(ps[:-1], b)
                newpacks.append((ps[:-1], b))

        if packs:
            newpacks.append((packs, bin))

        packlist.append(newpacks)


        costs.append(cost)

        # next iteration packages are of the last-added packages, the last box
        packages = newpacks[-1][0][-1]

    if len(costs) > 0:
        mincost = min(costs)
        minindex = costs.index(mincost)

        ret = packlist[minindex]
        return ret, []
    else:
        return [], rest


def binpack(packages, bins=None, iterlimit=5000):
    """Packs a list of Package() objects into a number of equal-sized bins.

    Returns a list of bins listing the packages within the bins and a list of packages which can't be
    packed because they are to big."""
    if bins is None:
        bins = [Package("600x400x400")]
    elif isinstance(bins, Package):
        bins = [bins]
    return iterate_permutations(packages, bins, iterlimit)


def test():
    fd = open('testdata.txt')
    vorher = 0
    nachher = 0
    start = time.time()
    for line in fd:
        packages = [Package(pack) for pack in line.strip().split()]
        if not packages:
            continue
        bins, rest = binpack(packages)
        if rest:
            print "invalid data", rest, line
        else:
            vorher += len(packages)
            nachher += len(bins)
    print time.time() - start,
    print vorher, nachher, float(nachher) / vorher * 100

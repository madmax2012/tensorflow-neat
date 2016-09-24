from Constants import OUTPUT0, OUTPUT1, INPUT1, INPUT0
from tensorflow_utils import build_and_test
import numpy as np


def add_connection(connections, genotype):
    enabled_innovations = [k for k in genotype.keys() if genotype[k]]

    enabled_connections = [connections[cns] for cns in enabled_innovations]

    # get reachable nodes
    froms = set([fr[1] for fr in enabled_connections ])
    tos = set([to[2] for to in enabled_connections])

    nodes = sorted(list(froms.union(tos)))

    # select random two:
    r1 = np.random.randint(0,len(nodes))
    r2 = np.random.randint(0,len(nodes) - 1)
    if r2 >= r1:
        r2 += 1

    r1 = nodes[r1]
    r2 = nodes[r2]
    from_node = r2 if r2 < r1 else r1
    to_node = r2 if r2 > r1 else r1

    assert(from_node < to_node)

    # prevent connections from input to input nodes and output to output nodes.
    # todo change this
    if from_node == INPUT0 and to_node == INPUT1 or from_node == OUTPUT0 and to_node == OUTPUT1:
        return add_connection( connections, genotype)

    # check if connection already there
    if not any(from_node == c[1] and to_node == c[2] for c in connections):
        connections.append((len(connections), from_node, to_node))

        genotype[len(connections) - 1 ] = True

    assert(len(genotype.keys()) <= len(connections))
    return connections, genotype


def add_node(connections, genotype, debug=False):
    # select random connection that is enabled
    enabled_innovations = [k for k in genotype.keys() if genotype[k]]

    # get random connection:
    r = np.random.randint(0,len(enabled_innovations))
    connections_innovation_index = enabled_innovations[r]
    connection_to_split = connections[connections_innovation_index]

    from_node = connection_to_split[1]
    to_node = connection_to_split[2]

    new_node = (to_node - from_node) / 2 + from_node

    if debug:
        print("from:", from_node)
        print("to:", to_node)
        print("new:", new_node)
    # todo: what to do if node id already exist? -> just leave it be.

    # add two new connection items: from_node -> new_node; new_node -> to_node
    # check if already existing beforehand.
    # todo: there should be a smarter way to do this than just give up.
    if not from_node < new_node:
        return connections, genotype
    if not new_node < to_node:
        return connections, genotype
    assert(from_node < new_node)
    assert(new_node < to_node)
    # check from to
    if not any(from_node == c[1] and new_node == c[2] for c in connections):
        id = len(connections)
        connections.append((id, from_node, new_node))
        genotype[id] = True
    else:
        ind = [c[0] for c in connections if c[1] == from_node and c[2] == new_node]
        genotype[ind[0]] = True

    if not any(new_node == c[1] and to_node == c[2] for c in connections):
        id = len(connections)
        connections.append((id, new_node, to_node))
        genotype[id] = True
    else:
        ind = [c[0] for c in connections if new_node == c[1] and to_node == c[2]]
        genotype[ind[0]] = True

    # add new node
    # disable old connection where we now inserted a new node
    genotype[connections_innovation_index] = False

    assert (len(genotype.keys()) <= len(connections))

    return connections, genotype




def crossover(connections, genotype0, performance0 , genotype1, performance1):
    # 1. matching genes are inherited at random (everything is made up and the weights don't matter here)
    # 2. disjoint and excess from the more fit parent
    # 3. preset chance to disable gene if its disabled in either parent

    # new genes should be always in the end
    k_0 = sorted(genotype0.keys())
    k_1 = sorted(genotype1.keys())

    # inherit disjoint from more fit parent
    offspring_genotype = {}
    if performance0 > performance1 and len(k_0) > len(k_1):
        # 0 is better and has more genes
        for l in connections:
            innovation_num = l[0]
            if innovation_num in k_0:
                offspring_genotype[innovation_num] = genotype0[innovation_num]
            elif innovation_num in k_1:
                offspring_genotype[innovation_num] = genotype1[innovation_num]

    elif performance1 > performance0 and len(k_1) > len(k_0):
        for l in connections:
            innovation_num = l[0]
            if innovation_num in k_1:
                offspring_genotype[innovation_num] = genotype1[innovation_num]
            elif innovation_num in k_0:
                offspring_genotype[innovation_num] = genotype0[innovation_num]

    elif len(k_1) < len(k_0):
        for k in k_1:
            offspring_genotype[k] = genotype1[k]

    elif len(k_0) <= len(k_1):
        for k in k_0:
            offspring_genotype[k] = genotype0[k]

    return offspring_genotype


def eval_fitness(connections, genotype, x, y, x_test, y_test, run_id="1"):
    perf_train = build_and_test(connections, genotype, x, y, x_test, y_test, run_id=run_id)
    return perf_train

def start_neuroevolution(x, y, x_test, y_test):
    """starts neuroevolution on binary dataset"""

    connections = [(0, INPUT0, OUTPUT0), (1, INPUT1, OUTPUT0), (2, INPUT0, OUTPUT1), (3, INPUT1, OUTPUT1)]
    genotypes = [{0: True, 1: True, 2: True, 3: True} for d in range(5)]

    for its in range(0,100):
        print( "iteration", its)

        fitnesses = []
        # test networks
        for i in range(0,len(genotypes)):
            fitnesses.append(eval_fitness(connections, genotypes[i], x, y, x_test, y_test, run_id=str(its) + "/" + str(i)))

        # get indices of sorted list
        fitnesses_sorted_indices = [i[0] for i in reversed(sorted(enumerate(fitnesses), key=lambda x: x[1]))]

        print("connections:\n")
        print(connections)
        for ra in range(0,len(fitnesses_sorted_indices)):
            print (fitnesses[fitnesses_sorted_indices[ra]], genotypes[fitnesses_sorted_indices[ra]])

        # run evolutions
        # todo: fiddle with parameters, include size of network in fitness?
        new_gen = []
        # copy five best survivors already
        m = 5
        if m > len(fitnesses):
            m = len(fitnesses)

        for i in range(0,m):
            print( "adding:", fitnesses[fitnesses_sorted_indices[i]], genotypes[fitnesses_sorted_indices[i]])
            new_gen.append(genotypes[fitnesses_sorted_indices[i]])

        for i in range(0,len(fitnesses_sorted_indices)):
            fi = fitnesses_sorted_indices[i]
            r = np.random.uniform()
            # select the best for mutation and breeding, kill of worst.
            if r <= 0.2:
                # mutate
                connections, gen = add_connection(connections, genotypes[i])
                new_gen.append(gen)
            r = np.random.uniform()
            if r <= 0.5:
                connections, gen = add_node(connections, genotypes[i])
                new_gen.append(gen)

            r = np.random.uniform()
            if r <= 0.1:
                # select random for breeding
                r = np.random.randint(0,len(fitnesses))
                r2 = np.random.randint(0,len(fitnesses) - 1)
                if r2 >= r:
                    r2 +=1
                gen = crossover(connections, genotypes[r], fitnesses[r], genotypes[r2], fitnesses[r2])
                new_gen.append(gen)
                new_gen.append(genotypes[fi])
                # stop if we have 5 candidates
            if len(new_gen) > 10:
                break
        genotypes = new_gen










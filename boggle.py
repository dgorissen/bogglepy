"""
Solving the boggle game using Python using straightforward recursion (no Tries).

For fun a sequential and parallel version of the solutoin routine can be run.

Code started its life as part of the 1 December 2011 London Python Dojo (Team 1).
"""

import random
import string 
import collections
from bisect import bisect_left
import time
import multiprocessing

def getDictionary(fname="words.txt"):
	"""
	Load the words into a dictionary with one entry for each letter (much faster than a flat list)
	To really do this fast you would use a Trie.
	"""
	word_dict = collections.defaultdict(list)
	with open(fname) as f:
		for w in f.readlines():
			if len(w) > 3:
				word_dict[w[0]].append(w.strip())

	return word_dict

def getGrid(size=8):
	"""
	Returns an square grid with a random letter in each cell
	"""
	grid = [[random.choice(string.ascii_lowercase) for c in range(size)] for r in range(size)]
	
	return grid

def getAdjacentLetters(grid, r, c):
	"""
	Given the boggle board and specific index on the board return a tuple (<letter>,<row idx>,<col idx>) for each
	of the neighbouring cells.  The origin is taken to be the top left corner
	"""
	
	# straightforward implementation where you pre-calculate all indices and then
	# remove the ones that are not needed if you are on the edge
	
	#size of the grid
	gsize = len(grid)
	
	# indexes of all neighbours for a given cell
	neighbours = [ [(r-1,c-1),(r-1,c),(r-1,c+1)],
				   [(r,c-1),          (r,c+1)],
				   [(r+1,c-1),(r+1,c) ,(r+1,c+1)] ]

	# simply remove the if's below if you want to add support for a grid that wraps round
	
	# if we are on the edge column of the grid
	if c == 0:
		# left edge -> keep the 2 rightmost columns
		res = [n[1:] for n in neighbours]
	elif c == gsize-1:
		# right edge -> keep the two leftmost colums
		res = [neighbours[0][0:2], [neighbours[1][0]], neighbours[2][0:2]]
	else:
		# somewhere in the grid, keep everything
		res = neighbours
	
	if r == 0:
		# top edge of the grid -> keep the bottom two rows 
		res = res[1:]
	elif r == gsize-1:
		# bottom edge -> keep the top two rows
		res = res[0:2]
	else:
		pass
	
	# now we have a correct list of the indices we need, create the necessary tuples
	
	letters = []
	for row in res:
		letters.extend( [(grid[r][c],r,c) for r,c in row] )

	return letters

def getPrefixMatches(word, dictionary):
	"""
	Looks for the word fragment in the dictionary and returns any valid matches.
	"""
	# Use the first letter of the word to get the correct section of the dictionary
	return [m for m in dictionary[word[0]] if m.startswith(word)]	

def isValidWord(word,dictionary):
	
	# Using bisection is a little bit faster but not worth it for the complexity:
	
	#wordlist = dictionary[word[0]]
	#i = bisect_left(wordlist, word)
	#if i != len(wordlist) and wordlist[i] == word:
	#	return True
	#return False

	# use the first letter of the word to get to the correct dictionary section
	return word in dictionary[word[0]]

def getWords(grid,dictionary,seed_letter,ply=64):
	"""
	Given a dictionary, boggle board, and starting point (as a (letter,r_idx,c_idx) tuple)
	return all the words that can be found from that position.  Ply can be used to limit
	the word length.
	"""
	
	# nested recursive function
	def genCandidates(results, seed_letter, ignored, curWord=""):

		if len(curWord) > ply:
			" -> maximum ply of %s reached, baling out" % ply
			return
		else:
			print "  trying ",curWord
		
		if isValidWord(curWord,dictionary):
			results.add(curWord)
			print "    -> match: ",curWord
		
		# make sure we dont visit the same letter twice
		ignored.add(seed_letter)
	
		# the neighbours of the seed cell
		neighbours = getAdjacentLetters(grid,seed_letter[1],seed_letter[2])
		
		# remove cells we have visited before by checking against the ignored list
		candidates = [n for n in neighbours if n not in ignored]
		
		# see how many words we can find for each candidate prefix
		num_matches = [len(getPrefixMatches(curWord + n[0], dictionary)) for n in candidates]
		
		# zip them together in a convenient list of tuples
		matches = zip(candidates,num_matches)
		
		# for each candidate with more than 0 matches recursively call the function
		for c,numMatches in matches:
			if numMatches > 0:
				genCandidates(results,c,ignored,curWord=curWord + c[0])
	

	# a set to keep track of the results
	results = set()
	
	# start the recursion
	genCandidates(results,seed_letter,set(),curWord=seed_letter[0])

	# some logging
	print "**********"
	print "Seed: ", seed_letter	
	print "--> %s words" % len(results)
	print "**********"

	return results

def solveSync(grid,dictionary,seeds,ply):
	"""
	Generate all words for each grid cell sequentially, using one CPU
	"""
	totResults = set()
	
	# iterate over every seed sequentially
	for seed in seeds:
		# the actual computation			
		results = getWords(grid,dictionary,seed,ply=ply)
		totResults = totResults.union(results)
	
	return totResults

def solveAsync(grid,dictionary,seeds,ply,cpus=None,chunksize=4):
	"""
	Generate all words for each grid cell in parallel, using multiple CPUs
	"""
	pool = multiprocessing.Pool(cpus) 
	asyncRes = pool.map_async(BoggleSolver(grid,dictionary,ply), seeds, chunksize=chunksize)
	res = asyncRes.get(10)
	
	# collect the results for all seeds
	totResults = set()
	for r in res:
		totResults = totResults.union(r)
	
	return totResults

class BoggleSolver:
	"""
	Helper class for the parallel solve
	We have to use a function object since lambda/partial cant be pickled in python 2
	See: http://stackoverflow.com/questions/4827432/how-to-let-pool-map-take-a-lambda-function
	"""
	def __init__(self,grid,dictionary,ply):
		self.grid = grid
		self.dict = dictionary
		self.ply = ply
		
	def __call__(self, seed):
		return getWords(self.grid,self.dict,seed,ply=self.ply)
		
def print_grid(grid):
	"""
	Simple utility method for displaying the grid
	"""
	for r in grid:
		print r

if __name__ == "__main__":

	dictionary = getDictionary()
	gsize = 8  # grid size
	ply = 64   # max word length

	"""
	# a fixed test grid
	grid = [
				['t', 'h', 'e', 'q', 'u', 'i', 'c', 'k'],
				['b', 'r', 'o', 'w', 'n', 'f', 'x', 'x'],
				['j', 'u', 'm', 'p', 'e', 'd', 'o', 'o'],
				['o', 'v', 'e', 'r', 't', 'h', 'e', 'l'],
				['a', 'z', 'y', 'd', 'o', 'g', 'j', 's'],
				['x', 'i', 'd', 'y', 'n', 'o', 'w', 'n'],
				['p', 'i', 'v', 's', 'm', 't', 'k', 'n'],
				['f', 'y', 'f', 'h', 'e', 'f', 'b', 'w']
			]
	"""
	
	# a random grid
	grid = getGrid(size=gsize)

	# display the grid
	print_grid(grid)
	
	# build the list of seed tuples (letter,row_idx,col_idx) for every item in the grid
	seeds = []
	for r,row in enumerate(grid):
		for c,letter in enumerate(row):
			seeds.append( (letter,r,c) )
	
	# start the timer
	tstart = time.time();

	# Solve sequentially with one process
	results = solveSync(grid,dictionary,seeds,ply)
	
	# Solve using multiple processes
	#results = solveAsync(grid,dictionary,seeds,ply)

	print "======================================================================================================="
	print "%s words with max %s letters found in a %sx%s grid after %s seconds: " % (len(results),ply,gsize,gsize,time.time() - tstart)
	print	
	print "   ",",".join(sorted(results))
	print "======================================================================================================="
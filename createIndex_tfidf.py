import gc
import math
import os
import re
import sys
import json
from array import array
from collections import defaultdict

from Naked.toolshed.shell import execute_js

from porterStemmer import PorterStemmer

porter = PorterStemmer()

class CreateIndex:
    def __init__(self):
        self.index = defaultdict(list)  # the inverted index
        self.titleIndex = {}            # Title Index
        self.tf = defaultdict(list)     # term frequencies of terms in documents

                                        # documents in the same order as in the main index
        self.df = defaultdict(int)      # document frequencies of terms in the corpus
        self.numDocuments = 0

    def getStopwords(self):
        '''get stopwords from the stopwords file'''
        f = open(self.stopwordsFile, 'r')
        stopwords = [line.rstrip() for line in f]
        self.sw = dict.fromkeys(stopwords)
        f.close()

    def getTerms(self, line):
        '''given a stream of text, get the terms from the text'''
        line = line.lower()
        line = line.strip()
        line = re.sub(r'[^a-z0-9 ]', ' ', line)  # put spaces instead of non-alphanumeric characters
        line = line.split()
        line = [x for x in line if x not in self.sw]  # eliminate the stopwords
        line = [porter.stem(word, 0, len(word) - 1) for word in line]
        return line


    def writeIndexToFile(self):
        '''write the index to the file'''
        # write main inverted index
        f = open(self.indexFile, 'w')
        # first line is the number of documents
        print >> f, self.numDocuments
        self.numDocuments = float(self.numDocuments)
        for term in self.index.iterkeys():
            postinglist = []
            for p in self.index[term]:
                docID = p[0]
                positions = p[1]
                postinglist.append(':'.join([str(docID), ','.join(map(str, positions))]))
            # print data
            postingData = ';'.join(postinglist)
            tfData = ','.join(map(str, self.tf[term]))
            idfData = '%.4f' % (self.numDocuments / self.df[term])
            print >> f, '|'.join((term, postingData, tfData, idfData))
        f.close()

        # write title index
        f = open(self.titleIndexFile, 'w')
        for pageid, title in self.titleIndex.iteritems():
            print >> f, pageid.encode('utf-8'), title.encode('utf-8')
        f.close()

    def getParams(self):
        '''get the parameters stopwords file, collection file, and the output index file'''
        param = sys.argv
        self.stopwordsFile = param[1]
        self.collectionFile = param[2]
        self.indexFile = param[3]
        self.titleIndexFile = param[4]

    def createIndex(self):
        '''main of the program, creates the index'''
        self.getParams()
        if os.path.isfile(self.collectionFile):
            data = json.load(open(self.collectionFile))
            self.collFile = data
            print 'Collection File Opened'
        else:
            success = execute_js('get-collections.js')
            if success:
                data = json.load(open(self.collectionFile))
                self.collFile = data
                print 'Collection File Opened'
            else:
                print 'Couldnt get collection!'

        print 'Reading in Stopwords'
        self.getStopwords()

        # bug in python garbage collector!
        # appending to list becomes O(N) instead of O(1) as the size grows if gc is enabled.
        gc.disable()

        # New Fields to test here
        data = self.collFile # Read in the dataset
        count = 0
        for entry in data['feed']['entry']:
            lines =  ''.join((entry['title'],entry['summary']))
            pageid = entry['id']
            terms = self.getTerms(lines)

            self.titleIndex[entry['id']] = entry['title']

            self.numDocuments += 1

            # build the index for the current page
            termdictPage = {}
            for position, term in enumerate(terms):
                try:
                    termdictPage[term][1].append(position)
                except:
                    termdictPage[term] = [pageid, array('I', [position])]

            # normalize the document vector
            norm = 0
            for term, posting in termdictPage.iteritems():
                norm += len(posting[1]) ** 2
            norm = math.sqrt(norm)

            # calculate the tf and df weights
            for term, posting in termdictPage.iteritems():
                self.tf[term].append('%.4f' % (len(posting[1]) / norm))
                self.df[term] += 1

            # merge the current page index with the main index
            for termPage, postingPage in termdictPage.iteritems():
                self.index[termPage].append(postingPage)

            print count
            count += 1

        gc.enable()         #Enable the garbage collector to free up memory and whatnot

        self.writeIndexToFile()     #Write the created index to file or maybe database

if __name__ == "__main__":
    c = CreateIndex()
    c.createIndex()



# coding: utf-8
# -*- coding: utf8 -*-

import Levenshtein  
import xml.etree.ElementTree
import codecs
import re
import json
import os

debug = False   
globalDelimeters= '#|،|\.|{|}|\n|؟|!|\(|\)|﴿|﴾|۞|۝|\*|-|\+|\:'

#------------------------------------
#General Utils
#------------------------------------

def normalizeText(text):
    """
        normalizes all forms to alf to ا, converts ة to ه, and ى to ي.  It also converts new lines and tabs to a single space
        and seperates common punctuation marks from text
    """

    search = ["أ", "إ", "آ", "ٱ", "ة", "_", "-", "/", ".", "،", " و ", '"', "ـ", "'", "ى", "ی", "\\", '\n', '\t',
              '&quot;', '?', '؟', '!', 'ﷲ']
    replace = ["ا", "ا", "ا", "ا", "ه", " ", " ", "", "", "", " و", "", "", "", "ي", "ي", "", ' ', ' ', ' ', ' ? ',
               ' ؟ ',' ! ', 'الله']

    # search = ["آ", "إ", "أ", "ة"]
    # replace = ["ا", "ا", "ا", "ه"]

    for i in range(0, len(search)):
        text = text.replace(search[i], replace[i])
    return text

def padSymbols(inTxt, symbolList = ['۞', '۝']):
    for sym in symbolList:
        inTxt = inTxt.replace(sym, ' '+sym+' ')
    return inTxt


def removeTashkeel(text):
    # Removes Tashkeel from input text

    p_tashkeel = re.compile(r'[\u0616-\u061A\u064B-\u0652\u06D6-\u06ED\u08F0-\u08F3\uFC5E-\uFC63\u0670]')
    text = re.sub(p_tashkeel, "", text)
    return text

def loadStops(fname):
    stopList = set([])
    fn = fname
    f = open(fn,'r', encoding='utf-8')
    for l in f:
       # l = l.decode('utf-8')
        l = l.strip()
        l = removeTashkeel(l)
        l= normalizeText(l)
        stopList.add(l)
    f.close()
    return stopList

def removeDelims(inStr, delims):
        l = re.split(delims, inStr)
        for x in l:
            x = x.strip()
            if(len(x) > 0):
                return x
        return ''
    
def normalizeTerm(t,delims =globalDelimeters):
    t = removeDelims(t,delims)
    if len(t) < 1:
        return ''
    t = removeTashkeel(t)
    t = normalizeText(t)
    return t.strip()

def getNextValidTerm(terms, delims, i):
    #given a list of terms and an index i, this method returns True if a valid term
    #can be found in that list, where a valid term is a term that is free from delimeter 
    #and false otherwise. If a valid term, is found, its normalized txt and index are returned
        l = len(terms)
        while i < l:
            eNorm =  normalizeTerm(terms[i],delims)
            if len(eNorm) > 1:
                return True, eNorm, i
            i = i+1
        return False, '', i

#Load Quaran into memory
def buildSuraIndex(indexFile):
    suras = []
    e = xml.etree.ElementTree.parse(indexFile).getroot()
    for atype in e.findall('sura'):
        suras.append(atype.get('name'))
    return suras

def buildVerseDics(s_names):
    d = {}
    for sura in s_names:
        d[sura] = {}
    return d


def addVerse(vText, vInfo, curr, strict, ambig,minLen,stops):
    # cText is the text to annotate, vInfo is a verse object, curr is the list to which to add the verse, and strict
    # is a boolean flag that indicates whether to check for invalid endings or not
    orig = curr
    vArray = vText.split()
    l = len(vArray)
    if l == 1:
        ambig.add(vText.strip())
    # print("len:", l)
    c = 0
    for w in vArray:
        c = c + 1
        # print (curr, w)
        if w in curr:
            # print("ye", w, curr)
            t = curr[w]
            curr = curr[w].childern
        else:
            t = term()
            t.str = w
            curr[w] = t
            curr = t.childern
        if c >= minLen:
            # print('y1')
            if strict:
                if not w in stops:
                    t.terminal = True
            else:
                t.terminal = True
            t.verses.add(vInfo)
        if c == l:
            # print('y2')
            t.absTerminal = True
            t.verses.add(vInfo)
    if (l - minLen) > 0:
        i = vText.index(" ") + 1
        addVerse(vText[i:], vInfo, orig, strict,ambig,minLen,stops)
        # print ("adding:", vText[i:])


def addAyat(fname, suras, all,qOrig,qNorm, ambig, minLen,stops):
    """
       Reads all verses in all suras and loads them in compact data structure to be used for matching. Expected format is:
        <sura_num>|<verse_num>|<verse>
        example: 1|1|بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
        The terms verse and aya are used interchangebly in this notebook
        """
     
    f = codecs.open(fname, "r", "utf-8")
    besm = 'بسم الله الرحمن الرحيم'
    lineNo = 1
    for line in f:
        line = line.strip()
        a = line.split("|")
        if len(a)<3:
            print("error in line:", lineNo)
            break
        lineNo = lineNo+1
        aIndex = int(a[0])-1
        ayaName = suras[aIndex]
        ayaNum = a[1]
        aya = a[2]
        ayaO = aya
        aya = normalizeText(aya)
        aya = removeTashkeel(aya)
        if (aIndex!=0) and (aya.startswith(besm)):
            newI = aya.index(besm)+ len(besm)
            aya = aya[newI:]
            ayaO = " ".join(ayaO.split()[4:])
            #print("mod:", aya)
        #print (ayaName, ayaNum, aya)
        qOrig[ayaName][ayaNum] = ayaO
        qNorm[ayaName][ayaNum] = aya
        v = verse(ayaName, ayaNum)
        addVerse(aya, v, all, True,ambig,minLen,stops)


#------------------------------------
#Class Definitions  
#------------------------------------
class verse:
    """Refers to  a single verse in Quran. 'name' is the name of the sura in which the verse appeared and number is the 
        number of the verse"""
    
    def __init__(self, name, number):
        self.name = name
        self.number = number
        
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.name == other.name) and (self.number== other.number)
        else:
            return False
        
    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.name)
    
    def print(self):
        print(self.name+":", self.number)
    
    def toStr(self):
        numStr = str(self.number)
        return self.name + ":" + numStr

class term:
     #A term refers to a node in the linked hash structure
    
    def __init__(self):
        self.str=""                #the text of a term in a verse 
        self.terminal = False      #Whether this term is a valid terminator for a verse or not 
        self.absTerminal = False   #whether this term is the actual terminator for a verse or not 
        self.verses = set([])      #the verses in which this term appears in a specific position preceded by a specific sequence 
        self.childern ={}          #a dictonary or hashtabe of terms that follow this term given 

    def print(self, spaces=""):
        print(spaces,self.str, self.terminal, self.absTerminal)
        for v in self.verses:
            v.print()
        c= 1
        for k in self.childern:
            sp = ""
            for s in range(0,c*2):
                sp = sp+" "
            self.childern[k].print(sp)
    
class matchRec:
    """This class is the main class used by the matcher to store informaion about a match. It is also what is returned as a
    result. """

    def __init__(self, v, n, si, ei, e, sit, eit):
        self.verses = [v]
        self.ayaName = n
        self.startIdx = si
        self.endIdx = ei
        self.errs = [e]
        self.startInText = sit
        self.endInText = eit

    def getStructured(self, json_format=False):
        result = {}
        result['aya_name'] = self.ayaName
        result['verses'] = self.verses
        result['errors'] = self.errs
        result['startInText'] = self.startInText
        result['endInText'] = self.endInText
        result['aya_start'] = self.startIdx
        result['aya_end'] = self.endIdx
        if json_format:
            return json.dumps(result, ensure_ascii=False).encode('utf8').decode()
        else:
            return result 
        
     
    def print(self):
        print(self.ayaName, self.startIdx, self.endIdx)
        if len(self.verses) != len(self.errs):
            print('error matching verses to errs')
            print(self.verses)
            print(self.errs)
            return
        i = 0
        for v in self.verses:
            print(v)
            print(i, self.errs[i])
            i = +1

    def getKey(self):
        return self.ayaName + str(self.startIdx)

    def getLen(self):
        l = 0
        for r in self.verses:
            l = l + len(r.split())
        return l

    def correctErrs(self, i, txt):
        tokens = txt.split()
        for e in self.errs[i]:
            err = e[0]
            corr = e[1]
            pos = e[2]
            tokens[pos] = corr
        return " ".join(tokens)

    def getExtraCnt(self, inL, extraList):
        cnt = 0
        for i in extraList:
            cnt = cnt + inL.count(i)
        return cnt


    def getStartIndex(self, t1, t2, nOrig):
        nTokens = nOrig.split()
        cnt = nTokens.count(t1)
        if cnt < 1:
            return -1
        if cnt == 1:
            return nTokens.index(t1)
        offset = 0
        for i in range(cnt):
            i1 = nTokens[offset:].index(t1) + offset
            #print('found ', t1, ',count:', cnt, 't2:', t2, 'next:', nTokens[i1 + 1])
            if nTokens[i1 + 1] == t2:
                #print('found index')
                return i1
            offset = i1 + len(t1)
        return -1

    def getErrNum(self):
        num = 0
        for e in self.errs:
            num = num + len(e)
        return num

    def getAdjusted(self, startIdx, startTerm, origTokens):
        l = len(origTokens)
        while (startIdx < l):
            curr =normalizeTerm(origTokens[startIdx])
            if  (curr== startTerm) or ('و' +curr == startTerm) or ('و'+startTerm == curr) :
                return startIdx
            startIdx = startIdx + 1
        return -1

    def getCorrectSpan(self, ridx, ayaName, qidx, oVerses, nVerses):
        # ridx is the index of the aya in the records verses (int)
        # qidx is the verse number in Q'uaran (str)
        extraList = ['ۖ', ' ۗ', 'ۚ', 'ۗ']
        orig = oVerses[ayaName][qidx]
        inTxt = self.verses[ridx]
        #inTxt = self.correctErrs(ridx, inTxt)
        origTokens = orig.split()
        origTokens = list(filter(lambda a: a != 'ۛ', origTokens))
        inTxtTokens = inTxt.split()
        # if (len(origTokens) - orig.count(' ۗ') - orig.count('ۚ')) > len(inTxtTokens):
        if (len(origTokens) - self.getExtraCnt(orig, extraList)) > len(inTxtTokens):
            # print('lorig:', len(origTokens), 'lin:',len(inTxtTokens))
            # print('orig:', orig)
            # print('in:', inTxt)
            # firstTwo = inTxtTokens[0] +' '+ inTxtTokens[1]
            nOrig = nVerses[ayaName][qidx]
            startIdx = self.getStartIndex(inTxtTokens[0], inTxtTokens[1], nOrig)
            # if not firstTwo in nOrig:
            if startIdx < 0:
                print('Something is very wrong (getCorrectSpan)')
                return orig
            # startIdx = nOrig.index(firstTwo)
            # print('start:', startIdx)
            if startIdx > 0:
                stStr = '...'
            else:
                stStr = ''
            # txtToCut = orig[0:startIdx]
            # print('cut: *'+txtToCut +'*' )
            # print('nor: *'+nOrig[0:startIdx] +'*' )
            # print(len(orig.split()), len(nOrig.split()))
            # print(orig)
            # print(nOrig)
            startIdx = startIdx + self.getExtraCnt(origTokens[0:startIdx], extraList)
            # print('startCorrected:', startIdx)
            # orig = orig[startIdx:]
            adjIdx = self.getAdjusted(startIdx, inTxtTokens[0], origTokens)
            if adjIdx > -1:
                startIdx = adjIdx
            origTokens = origTokens[startIdx:]
            l = len(inTxtTokens)
            result = origTokens[:l]
            # extra = result.count(' ۗ') + result.count('ۚ')
            extra = self.getExtraCnt(result, extraList)
            for i in range(extra):
                result.append(origTokens[l + i])
            endStr = '...'
            if len(origTokens) == len(result):
                endStr = ''
            return stStr + " ".join(result) + endStr
        #print('returning orig')
        return orig

    
    def getOrigStr(self, oVerses, nVerses):
        # oVerses are the original unnormalized verses
        # nVerses are the normalized Q'uran verses
        # the method returns the appropraite verses as they appear in Q'uran

        vCount = self.endIdx - self.startIdx + 1
        oStr = '"'
        endStr = '(' + self.ayaName + ':' + str(self.startIdx)
        if vCount > 1:
            endStr = endStr + '-' + str(self.endIdx)
        endStr = endStr + ')'
        for i in range(vCount - 1):
            oStr = oStr + self.getCorrectSpan(i, self.ayaName, str(self.startIdx + i), oVerses, nVerses) + '، '
        oStr = oStr + self.getCorrectSpan(vCount - 1, self.ayaName, str(self.startIdx + vCount - 1), oVerses,
                                          nVerses) + '"' + endStr
        return oStr


    def getStr(self):
        vCount = self.endIdx - self.startIdx + 1
        oStr = ''
        i=0
        for i in range(vCount - 1):
            oStr = oStr + self.verses[i] + ' '
        oStr = oStr + self.verses[i]
        return oStr


class qMatcherAnnotater():
    """ This is the main class that should be used for carrying out all matching and annotation tasks"""

    def __init__(self):
        suras = buildSuraIndex('dfiles/quran-index.xml')
        self.all = {}
        self.qOrig = buildVerseDics(suras)
        self.qNorm =  buildVerseDics(suras)
        self.stops =  loadStops('dfiles/nonTerminals.txt')
        self.ambig = set([])
        self.minLen = 3                                   #minimum acceptable match length 
        addAyat('dfiles/quran-simple.txt', suras, self.all,self.qOrig,self.qNorm, self.ambig, self.minLen,self.stops)
        self.besm = 'بسم الله الرحمن الرحيم'
        #Expand this list for any verses that should not be matched if they appear alone 
        self.stopVerses = [self.besm, 'الله ونعم الوكيل', 'الحمد لله' ]

        print("Done loading..  ")


    def getStopPercentage(self, inStr):
        #returns the percentage of stop terms in string inStr 
        terms = inStr.split()
        strLen = len(terms)
        num = 0
        for t in terms:
            if t in self.stops:
                num = num + 1
            elif t.startswith("و") and t[1:] in self.stops:
                num = num + 1
        per = num / strLen
        return per

    def findInChildren(self, inStr, curr):
        #This function takes in a term insStr and a hashmap/dictionary curr (containing multipe nodes), and if the term 
        #is a child of any of those nodes. If it is, this node is returned.  
        for c in curr:
            if inStr in curr[c].childern:
                return c
        return 0

    def matchWithError(self, inStr, curr):
        for t in curr:
            if Levenshtein.distance(inStr, t) == 1 and (not t in self.ambig):
                return t
        return 0


    def getErrored(self, txt, errs):
        for e in errs:
            txt = txt.replace(e[1], e[0])
        return txt

    def updateResults(self, k, memAya, memVs, mem, result, er, cv, end):
        idx = memAya.index(k.name)
        if debug:
            print(k.number)
            print('===memAya', memAya)
            print('===memVs', memVs)
            print('===mem', mem)
            print('===result', result)
            print('===er', er)
            print('===cv', cv)
            print('===end', end)

        # if debug: print("idx", memVs[idx])
        prev = int(k.number) - 1
        if prev == memVs[idx]:
            active = 0
            recs = result[k.name]
            if len(recs) == 1:
                active = recs[0]
            else:
                for r in recs:
                    if r.endIdx == prev:
                        active = r
                        break
            # print('found active')
            # active.print()
            active.verses.append(cv)
            active.endIdx = int(k.number)
            active.endInText = end
            active.errs.append(er)
            for g in range(len(mem)):
                if g != idx:
                    nTodel = mem[g].split(':')[0]
                    idxToDel = mem[g].split(':')[1]
                    # print('deleting:',mem[g] )
                    recs = result[nTodel]
                    if len(recs) > 1:
                        cnt = 0
                        for r in recs:
                            if r.startIdx == idxToDel:
                                recs.pop(cnt)
                                break
                            cnt = +1
                    """
                    else:
                        del result[nTodel]
                    """
            memAya.clear()
            memVs.clear()
            mem.clear()
            # print('memory', memAya, memVs, mem)
            return False
        else:
            # print('not sequential', prev, memVs[idx], type(prev), type(memVs[idx]) )
            memAya.pop(idx)
            memVs.pop(idx)
            mem.pop(idx)
            return True
   
    def matchDetectMissingVerse(self, terms, curr, startIdx, delims, findErr):
        #Current issues: If the missing word is the last word in a verse, it will not be detected.
        
        errors = []
        errs = []
        #terms = inStr.split()
        result = set([])
        rStr = ""
        rStrFinal = ""
        resultFinal = set([])
        wdCounter, endIdx = startIdx-1, 0
        
        for t in terms[startIdx:]:
            wdCounter = wdCounter+1
            t = normalizeTerm(t,delims)
            if len(t) < 1:
                continue
            e = False
            if (not t in curr) and (findErr):
                e = self.matchWithError(t, curr)
                if e:
                    errors.append((t, e, wdCounter))
                    t = e
            if t in curr:
                rStr = rStr + t + " "
                result = curr[t].verses
                if (curr[t].terminal) or (curr[t].absTerminal):
                    rStrFinal = rStr
                    resultFinal = result
                    errs = errors
                    endIdx = wdCounter +1
                curr = curr[t].childern
            else:
                # this code detects missing words
                # Sample output
                # Input string: 'لكل جعلنا شرعه ومنهاجا',
                # errors: [('شرعه', 'منكم شرعه')])
                missing = self.findInChildren(t, curr)
                if (missing):
                    rStr = rStr + missing + " " + t +" "
                    tempCur = curr[missing].childern
                    result = tempCur[t].verses
                    errors.append((t, missing + " " + t, wdCounter))
                    if len(rStr.split()) > self.minLen and (tempCur[t].terminal or tempCur[t].absTerminal):
                        rStrFinal = rStr
                        resultFinal = result
                        errs = errors
                        endIdx = wdCounter +1 
                    curr = tempCur[t].childern
                else:
                    #print('missing 2 ',t)
                    ##LookAhead oneword
                    next_term_exists, next_term, indx = getNextValidTerm(terms, delims, wdCounter+1)
                    if not (next_term_exists):
                        return resultFinal, rStrFinal.strip(), errs, endIdx
                    valid = self.findInChildren(next_term, curr)
                    if valid:
                        #print('missing 3 ',t)
                        errors.append((t, valid, wdCounter))
                        rStr = rStr + t + " "
                        curr = curr[valid].childern
                        endIdx = indx +1
                        #count = indx
                    else:
                        return resultFinal, rStrFinal.strip(), errs, endIdx
        return resultFinal, rStrFinal.strip(), errs, endIdx 
    

    def matchSingleVerse(self, terms, curr, startIdx, delims, findErr):
        errors = []
        errs = []
        #terms = inStr.split()[startIdx:]
        result = set([])
        rStr = ""
        rStrFinal = ""          #the text of the matching verse
        resultFinal = set([])   #a set of all verses that contain the verse
        wdCounter, endIdx = startIdx-1, 0

        for t in terms[startIdx:]:
            wdCounter = wdCounter+1
            t = normalizeTerm(t,delims)
            if len(t) < 1:
                continue
            e = False
            if (not t in curr) and (findErr):
                e = self.matchWithError(t, curr)
                if e:
                    if debug: print("err:", t, e,wdCounter, terms[wdCounter])
                    errors.append((t, e, wdCounter))
                    t = e
            if t in curr:
                rStr = rStr + t + " "
                result = curr[t].verses
                if (curr[t].terminal) or (curr[t].absTerminal):
                    rStrFinal = rStr
                    resultFinal = result
                    errs = errors
                    endIdx = wdCounter + 1
                curr = curr[t].childern
            else:
                if debug: print(t, "not found" )
                return resultFinal, rStrFinal.strip(), errs,endIdx
        return resultFinal, rStrFinal.strip(), errs, endIdx

    def matchLongVerse(self, terms, curr, startIdx, delims, findErr):
        #A utility method that should be called by other methods 
        #Returns the longest verse that can be matched in a str represented by a list of terms 
        #accounting for minor error such as an extra waw or other character at the begining of a verse
        #Only works if the first term in the string is a word that can be found in Q'uran 
        
        if not findErr:
            return self.matchSingleVerse(terms, curr,startIdx, delims, findErr)
        #terms = inStr.split()
        term = terms[startIdx]
        first = normalizeTerm(term,delims)
        e = "و" + first
        found = False
        rf2, rs2, err2, end2 = 0, 0, 0, 0
        if first.startswith("و") and first[1:] in curr:
            found = True
        if len(terms[startIdx:]) > 0 and not e in curr and not found:
            return self.matchSingleVerse(terms, curr,startIdx, delims, findErr)
       
        rf1, rs1, err1, end1 = self.matchSingleVerse(terms, curr,startIdx, delims, findErr)
        if (not found):
            terms[startIdx] = "و" + first 
            rf2, rs2, err2,end2 = self.matchSingleVerse(terms, curr, startIdx, delims, findErr)
            err2.append(( first, terms[startIdx], startIdx))
            terms[startIdx] =  term 
        else:
            terms[startIdx] = first [1:]
            rf2, rs2, err2, end2 = self.matchSingleVerse(terms, curr, startIdx, delims, findErr)
            err2.append((first, first[1:], startIdx))
            terms[startIdx] =  term 
        if len(rs2) > len(rs1):
            return rf2, rs2, err2, end2
        
        else:
            return rf1, rs1, err1, end1
        
    def matchLongVerseDetectMissing(self, terms, curr, startIdx, delims,findErr):
        #terms = inStr.split()
        term = terms[startIdx]
        first = normalizeTerm(term,delims)
        e = "و" + first
        found = False
        rf2, rs2, err2, end2 = 0, 0, 0, 0
        
        if first.startswith("و") and first[1:] in curr:
            found = True
        if debug: print('fnd:', found)
        if len(terms[startIdx:]) > 0 and not e in curr and not found:
            # print('yes', inStr, terms[0])
            return self.matchDetectMissingVerse(terms, curr,startIdx, delims, findErr)
        rf1, rs1, err1, end1 = self.matchDetectMissingVerse(terms, curr,startIdx, delims, findErr)
        if len(rs1.split()) == len(terms[startIdx:]):
            return rf1, rs1, err1, end1
        if (not found):
            terms[startIdx] = "و" + first 
            rf2, rs2, err2,end2 = self.matchDetectMissingVerse( terms, curr, startIdx, delims, findErr)
            err2.append(( first, terms[startIdx], startIdx))
            terms[startIdx] =  term 
        else:
            terms[startIdx] = first[1:]
            rf2, rs2, err2,end2 = self.matchDetectMissingVerse(terms, curr, startIdx, delims, findErr)
            err2.append((first, first[1:], startIdx))
            terms[startIdx] =  term 
        if len(rs2.split()) > len(rs1.split()):
            return rf2, rs2, err2, end2
        else:
            return rf1, rs1, err1, end1

    def locateVerseWithName(self, name, verses):
        for r in verses:
            if r.name == name:
                return r
        return -1
    
    def matchVersesInText(self, inStr, curr, findErr=True, findMissing=False, delims=globalDelimeters):
       
        #given any peice of text, return a list of all quaranic verses that appear in that text. 
        
        result = {}
        memAya = []
        memVs = []
        mem = []
        errs = []
        
        cuurStartIdx = 0
        terms = inStr.split()
        i = 0
        while i < len(terms):
            end = -1
            valid, t, i = getNextValidTerm(terms, delims, i)
            if not valid:
                return result, errs 
            v = "و" + t
            z = t[1:]
            if t in curr or v in curr or z in curr:
                # if t in curr:
                # print("cline:" , currLine)
                r, rStr, er = [], "", []
                if findMissing:
                    r, rStr, er, end = self.matchLongVerseDetectMissing(terms, self.all,i, delims, findErr)
                else:
                    r, rStr, er, end = self.matchLongVerse(terms, self.all,i, delims,findErr)
                    if debug: print("gotback:", rStr)
                if len(r) == 0:
                    memAya = []
                    memVs = []
                    mem = []
                    i = i + 1
                    continue 

                errs = errs + er
                # if debug: print(memAya, memVs, mem)
                currAyat = [x.name for x in r]
                #print('currAyat:', currAyat)
                overlap = list(set(currAyat).intersection(set(memAya)))
                #print('overlap:', overlap)
                found = False 
                if len(overlap) > 0:
                    if debug: print ("matched verse: ", rStr)
                    #print(len(r))
                    start = i
                    #print('start', start)
                    for vName in overlap:
                        k = self.locateVerseWithName(vName,r)
                        # if debug: k.print()
                        createNewRec = self.updateResults(k, memAya, memVs, mem, result, er, rStr, end)
                        found = not createNewRec
                        aya = k.toStr()
                        memAya.append(k.name)
                        memVs.append(int(k.number))
                        mem.append(aya)
                    if found: i = i + len(rStr.split())
            
                if (not found) and len(r)>0:
                    start = i
                    for k in r:
                        aya = k.toStr()
                        memAya.append(k.name)
                        memVs.append(int(k.number))
                        mem.append(aya)
                        # print('after:', memAya,memVs, mem)
                        if k.name in result:
                            newRec = matchRec(rStr, k.name, int(k.number), int(k.number), er, start, end)
                            result[k.name].append(newRec)
                        else:
                            newRec = matchRec(rStr, k.name, int(k.number), int(k.number), er, start, end)
                            result[k.name] = [newRec]

                    i = i + len(rStr.split())
            else:
                i = i + 1
            if end >0:
                i = end 
        return result, errs

    def isValidRec(self, r, allowedErrPers=0.25, minMatch=3):
        # allowedStopTable is a dictionary with the key as the number of words and the value is the
        # allowable number of stopword there. So for example, if a verse has 4 words, according to the
        # default, only 1 of those is allowed to be a stop word, if it has 3, then it cant have any

        l = r.getLen()
        if r.getLen() < minMatch:
            # print("Checkpoing 1:" , r.getLen(), r)
            return False

        if r.getErrNum() >= allowedErrPers * l:
            return False
        if len(r.verses) == 1:
            if r.verses[0] in self.stopVerses:
                return False
            v_len = len(r.verses[0].split())
            if v_len < 6:
                allowedFactor = (v_len-3) / v_len
                if self.getStopPercentage(r.verses[0]) > allowedFactor:
                    # rint("checkpoint 3:" , len(r.verses[0].split()),  self.getStopPercentage(r.verses[0]) )
                    return False
        return True
        
    def annotateTxt(self, inText, findErrs= True, findMissing = True, d = globalDelimeters):

        inText = padSymbols(inText)
        recs, errs = self.matchVersesInText(inText, self.all, findErrs, findMissing, d)
        seen = []
        allTerms = inText.split()
        replacmentIndex = 0
        result = ""
        seen = []
        replacmentRecs = {}
        replacmentTexts = {}

        for v in recs:
            matches = recs[v]
            for r in matches:
                if not self.isValidRec(r):
                    continue
                cText = r.getOrigStr(self.qOrig, self.qNorm)
                currLoc = (r.startInText,r.endInText)
                if not currLoc in seen :
                    #print(r.startInText, r.endInText)
                    replacmentRecs[currLoc[0]] = r
                    replacmentTexts[currLoc[0]] = cText
                seen.append(currLoc)

        texts = [r for r in sorted(replacmentRecs)]
        #print('len txts:', len(texts))
        for idx in texts:
            r = replacmentRecs[idx]
            result = result + " ".join(allTerms[replacmentIndex:r.startInText]) + replacmentTexts[idx] +' '
            replacmentIndex = r.endInText
        result = result.strip() +  " ".join(allTerms[replacmentIndex:])
        return result

    def matchAll(self, inText, findErr=True, findMissing=True, d=globalDelimeters, minMatch = 3, allowedErrPers = 0.25,  
                 return_json=False):

        inText = padSymbols(inText)
        recs, errs = self.matchVersesInText(inText, self.all, findErr, findMissing)
        result = []

        for v in recs:
            matches = recs[v]
            for r in matches:
                if not self.isValidRec(r):
                    continue
                result.append(r.getStructured(json_format =return_json ))


        return result

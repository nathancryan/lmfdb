from pymongo import WriteConcern
from time import time
#
# rewrite_collection(db,incoll,outcoll,func)
#
# function to pipe an existing collection to a new collection through a user specified function
# that may update records as the pass through.  All indexes will be recreated (in lex order),
# unless reindex is set to false.
#
# Arguments:
#
#    db: should be a mongo database to which the caller has write access (authenticate as editor)
#    incoll: the name of the input collection in db
#    outcoll: the name of the output collection (must not already exist in db)
#    func: filter that takes a mongo db document (dictionary) and returns a (possibly) updated version of it
#
# Example usage: rewrite_collection(db,"old_stuff","new_stuff",lambda x: x)
#
# For collections with large records, you will want to specify a batchsize smaller than 1000
#
def rewrite_collection(db,incoll,outcoll,func, batchsize=1000, reindex=True):
    if outcoll in db.collection_names():
        print "Collection %s already exists, unable to write"%(outcoll)
        return
    start = time()
    inrecs = db[incoll].find()
    # increase wtimeout to avoid BulkWriteErrors caused by timeouts
    db.create_collection(outcoll,write_concern=WriteConcern(wtimeout=int(60000)))
    outrecs = []
    cnt = 0
    tot = inrecs.count()
    for r in inrecs:
        r.pop('_id') # remove mongo db id attribute
        outrecs.append(func(r))
        cnt += 1
        if len(outrecs) >= batchsize:
            db[outcoll].insert_many(outrecs)
            print "%d of %d records (%.1f percent) inserted in %.3f secs"%(cnt,tot,100.0*cnt/tot,time()-start)
            outrecs=[]
    if outrecs:
        db[outcoll].insert_many(outrecs)
    assert db[outcoll].count() == tot
    print "inserted %d records in %.3f secs"%(cnt, time()-start)
    if reindex:
        reindex_collection(db,incoll,outcoll)
    print "Rewrote %s to %s, total time %.3f secs"%(incoll, outcoll, time()-start)

# reindex_collection(db,incoll,outcoll)
#
# Take indexes from incoll and create them in outcoll (in lex order).
#
def reindex_collection(db,incoll,outcoll):
    indexes = db[incoll].index_information()
    keys = [(k,indexes[k]['key']) for k in indexes if k != '_id_']
    keys.sort() # sort indexes by keyname so (attr1) < (attr1,attr2) < (attr1,attr2,attr3) < ...
    for i in range(len(keys)):
        now = time()
        key = [(a[0],int(1) if a[1] > 0 else int(-1)) for a in keys[i][1]] # deal with legacy floats (1.0 vs 1)
        db[outcoll].create_index(key)
        print "created index %s in %.3f secs"%(keys[i][0],time()-now)



#!/usr/bin/env python3
# Copyright (c) 2014-2016 The Bitcoin Core developers
# Copyright (c) 2021 The Dogecoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

# Test mempool behavior when spammed with min_relay vs recommended fee

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *

import itertools as it

class MempoolSpamTest(BitcoinTestFramework):

    def setup_network(self):
        self.nodes = []
        for _ in range(self.num_nodes):
            self.new_node()
        connect_nodes(self.nodes[0], 1)
        self.is_network_split = False
        self.sync_all()
        self.relayfee = self.nodes[0].getnetworkinfo()['relayfee']

    def __init__(self):
        super().__init__()
        self.setup_clean_chain = True
        self.num_nodes = 2

        self.txouts = gen_return_txouts()

    def new_node(self):
        self.nodes.append(start_node(len(self.nodes), self.options.tmpdir, ["-minrelaytxfee=0.001", "-maxmempool=500", "-spendzeroconfchange=0", "-debug"]))

    def run_test(self):
        txids = []
        utxos = create_confirmed_utxos(self.relayfee, self.nodes[0], 181)

        self.sync_all()

        for i in range (2):
            txids.append([])
            txids[i] = create_lots_of_big_transactions(self.nodes[0], self.txouts, utxos[30*i:30*i+30], 30, self.relayfee * i)
            self.sync_all()

        #create a mempool tx with fee > self.txouts
        us0 = utxos.pop()
        inputs = [{ "txid" : us0["txid"], "vout" : us0["vout"]}]
        outputs = {self.nodes[0].getnewaddress() : 1}
        tx = self.nodes[0].createrawtransaction(inputs, outputs)
        self.nodes[0].settxfee(self.relayfee*25) # specifically fund this tx with higher fee
        txF = self.nodes[0].fundrawtransaction(tx)
        self.nodes[0].settxfee(0) # return to automatic fee selection
        txFS = self.nodes[0].signrawtransaction(txF['hex'])
        txid = self.nodes[0].sendrawtransaction(txFS['hex'])

        for i in range (2,4):
            txids.append([])
            txids[i] = create_lots_of_big_transactions(self.nodes[0], self.txouts, utxos[30*i:30*i+30], 30, self.relayfee*i)
            self.sync_all()

        # our transaction should still live in the mempool
        assert(self.nodes[0].getmempoolinfo()['size'] == self.nodes[1].getmempoolinfo()['size'])
        for i in range(self.num_nodes):
            assert(txid in self.nodes[i].getrawmempool())
            #assert(self.nodes[1].getmempoolinfo()['size'] < sum(1 for _ in it.chain.from_iterable(txids)))

        # mine a block on node 1
        self.nodes[1].generate(1)
        self.sync_all()

        # our transaction should be mined
        for i in range(self.num_nodes):
            assert(txid not in self.nodes[i].getrawmempool())

if __name__ == '__main__':
    MempoolSpamTest().main()

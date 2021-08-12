#!/usr/bin/env python3
# Copyright (c) 2021 The Dogecoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Dogecoin Fee QA test.

# Tests miner, relay and wallet fee behaviors
# of active and planned node versions
# using the default parametrizations
"""

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *
from decimal import Decimal

TYPE_MINER = 0
TYPE_RELAY = 1
TYPE_WALLET = 2

class DogecoinFeesTest(BitcoinTestFramework):

    def __init__(self):
        super().__init__()
        self.setup_clean_chain = True
        self.define_node_parametrization()
        self.num_versions = len(self.paramset.keys())
        self.num_nodes = self.num_versions * 3


    def define_node_parametrization(self):
        # v1.14.2 - v1.14.3 default parametrization
        params_01140300 = [
            "-blockmintxfee=0.00001",
            "-minrelaytxfee=1",
            "-paytxfee=1",
            "-mintxfee=1",
            "-dustlimit=1",
            "-txindex",
            "-debug"
        ]

        # planned v1.14.4 default parametrization
        # TODO: remove hardcoded params when the policy is fully implemented.
        params_01140400 = [
            #"-blockmintxfee=0.01",
            #"-minrelaytxfee=0.001",
            #"-paytxfee=1",
            #"-mintxfee=1",
            #"-dustlimit=0.001",
            "-txindex",
            "-debug"
        ]

        # planned v1.14.5 default parametrization
        params_01140500 = [
            "-blockmintxfee=0.01",
            "-minrelaytxfee=0.001",
            "-paytxfee=0.01",
            "-mintxfee=0.01",
            "-dustlimit=0.001",
            "-txindex",
            "-debug"
        ]

        self.paramset = {
            "01140300": params_01140300,
            "01140400": params_01140400,
            "01140500": params_01140500
        }

    def setup_node(self, version, node_type):
        if not version in self.paramset:
            raise AssertionError("Unknown version: " + version)

        if node_type >= 3:
            raise AssertionError("node_type should be < 3")

        if not version in self.nodemap:
            self.nodemap[version] = {}

        if node_type in self.nodemap[version]:
            raise AssertionError("Cannot instantiate node with duplicate version/type")

        next_idx = len(self.nodes)
        node = start_node(next_idx, self.options.tmpdir, self.paramset[version])

        self.nodemap[version][node_type] = node
        self.nodes.append(node)

    def setup_network(self, split=False):
        self.nodes = []
        self.nodemap = {}

        n = self.num_versions

        for v in self.paramset.keys():
            for i in range(3):
                self.setup_node(v, i)

        # connect all nodes
        for i in range(self.num_nodes - 1):
            for c in range(i + 1, self.num_nodes):
                connect_nodes_bi(self.nodes, i, c)

        self.legacy_miner = self.get_nodes("01140300", TYPE_MINER)[0]
        self.is_network_split=False
        self.sync_all()

    def run_test(self):

        self.seed = 1000 # the amount to seed wallets with
        self.amount = 49 # the amount to send back
        self.target_address = self.legacy_miner.getnewaddress()

        # mine some blocks using the oldest version
        self.legacy_miner.generate(102)

        # send some coins to each leaf wallet node
        for n in self.get_nodes(None, TYPE_WALLET):
            self.legacy_miner.sendtoaddress(n.getnewaddress(), self.seed)

        # mine the tx
        self.legacy_miner.generate(5)
        self.sync_all()

        # run the tests
        self.test_01140300_to_all()
        self.test_01140400_to_all()
        self.test_01140500_to_01140400()

        # make sure finally every version agrees on blocks and mempool
        self.sync_all()

    def test_01140400_to_all(self):
        wallet = self.get_nodes("01140400", TYPE_WALLET)[0]
        txid = wallet.sendtoaddress(self.target_address, self.amount)
        self.sync_all() # everyone must see this tx
        self.legacy_miner.generate(1) # mine a block
        self.sync_all() # everyone must get the new block
        assert_equal(wallet.getmempoolinfo()['size'], 0) # this tx was mined

    def test_01140300_to_all(self):
        wallet = self.get_nodes("01140300", TYPE_WALLET)[0]
        miner = self.get_nodes("01140400", TYPE_MINER)[0]
        txid = wallet.sendtoaddress(self.target_address, self.amount)
        self.sync_all() # everyone must see this tx
        miner.generate(1) # mine a block with 1.14.4
        self.sync_all() # everyone must get the new block
        assert_equal(wallet.getmempoolinfo()['size'], 0) # this tx was mined

    def test_01140500_to_01140400(self):
        wallet = self.get_nodes("01140500", TYPE_WALLET)[0] # 1.14.5 wallet
        miner = self.get_nodes("01140400", TYPE_MINER)[0] # 1.14.4 miner
        txid = wallet.sendtoaddress(self.target_address, self.amount)
        sync_mempools(self.get_nodes("01140400") + self.get_nodes("01140500")) # all v1.14.4+ nodes see this
        sync_mempools(self.get_nodes("01140300")) # separately ensure 1.14.3 consistency

        # v1.14.3 nodes do not see this transaction
        for node in self.get_nodes("01140300"):
            assert_equal(node.getmempoolinfo()['size'], 0)

        # mine a block with 1.14.3
        self.legacy_miner.generate(1)
        sync_blocks(self.nodes) # everyone must get the new block
        assert_equal(wallet.getmempoolinfo()['size'], 1) # this tx was NOT mined

        # mine a block with 1.14.4
        miner.generate(1)
        self.sync_all() # everyone must get the new block and mempools must all be empty
        assert_equal(wallet.getmempoolinfo()['size'], 0) # this tx was mined

    def get_nodes(self, version=None, node_type=-1):
        if not version is None and not version in self.paramset:
            raise AssertionError("version not defined")

        if node_type >= 3:
            raise AssertionError("node_type must be < 3")

        if version is None and node_type < 0:
            return self.nodes

        lnodes = []

        if version is None:
            for v in self.paramset.keys():
                lnodes.append(self.nodemap[v][node_type])
            return lnodes

        if node_type < 0:
            for t in range(3):
                lnodes.append(self.nodemap[version][t])
            return lnodes

        return [ self.nodemap[version][node_type] ]


if __name__ == '__main__':
    DogecoinFeesTest().main()

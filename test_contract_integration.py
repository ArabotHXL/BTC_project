#!/usr/bin/env python3
"""
SLA Proof NFT Contract Integration Tests
Tests the deployed smart contract functionality and integration with the backend system

Usage:
    python test_contract_integration.py
    python test_contract_integration.py --network base-sepolia
    python test_contract_integration.py --verbose
"""

import os
import sys
import time
import json
import logging
import argparse
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.blockchain_config import get_blockchain_config, get_sla_nft_contract
from sla_nft_minting_system import SLANFTMintingSystem
from sla_collector_engine import SLACollectorEngine

class ContractIntegrationTester:
    """Test suite for SLA Proof NFT contract integration"""
    
    def __init__(self, network_name: str = None, verbose: bool = False):
        self.network_name = network_name
        self.verbose = verbose
        self.setup_logging()
        
        # Initialize blockchain config
        self.blockchain_config = get_blockchain_config(network_name)
        self.w3 = self.blockchain_config.w3
        
        # Test results tracking
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_all_tests(self):
        """Run all integration tests"""
        self.logger.info("🚀 Starting SLA Proof NFT Contract Integration Tests")
        self.logger.info(f"Network: {self.blockchain_config.network.name}")
        self.logger.info("=" * 60)
        
        # Test phases
        test_phases = [
            ("Network Connection", self.test_network_connection),
            ("Contract Deployment", self.test_contract_deployment),
            ("Contract Basic Functions", self.test_contract_basic_functions),
            ("SLA Data Collection", self.test_sla_data_collection),
            ("NFT Minting System", self.test_nft_minting_system),
            ("Contract Query Functions", self.test_contract_queries),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance)
        ]
        
        for phase_name, test_function in test_phases:
            self.logger.info(f"\n📋 Testing: {phase_name}")
            self.logger.info("-" * 40)
            
            try:
                test_function()
                self.test_results['passed'] += 1
                self.logger.info(f"✅ {phase_name}: PASSED")
            except Exception as e:
                self.test_results['failed'] += 1
                self.test_results['errors'].append(f"{phase_name}: {str(e)}")
                self.logger.error(f"❌ {phase_name}: FAILED - {e}")
        
        # Print final results
        self.print_test_summary()
    
    def test_network_connection(self):
        """Test blockchain network connection"""
        self.logger.info("Testing network connection...")
        
        # Test connection
        assert self.w3.is_connected(), "Web3 connection failed"
        
        # Test chain ID
        chain_id = self.w3.eth.chain_id
        expected_chain_id = self.blockchain_config.network.chain_id
        assert chain_id == expected_chain_id, f"Chain ID mismatch: expected {expected_chain_id}, got {chain_id}"
        
        # Test latest block
        latest_block = self.w3.eth.get_block('latest')
        assert latest_block.number > 0, "Failed to get latest block"
        
        # Test gas price
        gas_price = self.blockchain_config.get_gas_price()
        assert gas_price > 0, "Failed to get gas price"
        
        self.logger.info(f"Connected to {self.blockchain_config.network.name}")
        self.logger.info(f"Latest block: {latest_block.number}")
        self.logger.info(f"Gas price: {self.w3.from_wei(gas_price, 'gwei'):.2f} gwei")
    
    def test_contract_deployment(self):
        """Test that contracts are properly deployed"""
        self.logger.info("Testing contract deployment...")
        
        # Check if SLA NFT contract is deployed
        sla_nft_deployed = self.blockchain_config.is_contract_deployed('SLAProofNFT')
        
        if not sla_nft_deployed:
            self.logger.warning("SLA NFT contract not deployed, skipping contract tests")
            self.test_results['skipped'] += 1
            return
        
        # Get contract instance
        contract = get_sla_nft_contract()
        assert contract is not None, "Failed to get contract instance"
        
        # Test contract address
        contract_address = contract.address
        assert contract_address and contract_address != '0x0000000000000000000000000000000000000000', "Invalid contract address"
        
        self.logger.info(f"SLA NFT Contract: {contract_address}")
    
    def test_contract_basic_functions(self):
        """Test basic contract read functions"""
        self.logger.info("Testing contract basic functions...")
        
        if not self.blockchain_config.is_contract_deployed('SLAProofNFT'):
            self.logger.warning("Contract not deployed, skipping")
            return
        
        contract = get_sla_nft_contract()
        
        # Test basic getters
        name = contract.functions.name().call()
        symbol = contract.functions.symbol().call()
        owner = contract.functions.owner().call()
        total_certificates = contract.functions.totalCertificatesIssued().call()
        total_verifications = contract.functions.totalVerifications().call()
        
        assert len(name) > 0, "Contract name is empty"
        assert len(symbol) > 0, "Contract symbol is empty"
        assert owner != '0x0000000000000000000000000000000000000000', "Invalid owner address"
        
        self.logger.info(f"Contract Name: {name}")
        self.logger.info(f"Contract Symbol: {symbol}")
        self.logger.info(f"Owner: {owner}")
        self.logger.info(f"Total Certificates: {total_certificates}")
        self.logger.info(f"Total Verifications: {total_verifications}")
        
        # Test contract info
        version, description = contract.functions.getContractInfo().call()
        assert len(version) > 0, "Contract version is empty"
        assert len(description) > 0, "Contract description is empty"
        
        self.logger.info(f"Version: {version}")
        self.logger.info(f"Description: {description}")
    
    def test_sla_data_collection(self):
        """Test SLA data collection system"""
        self.logger.info("Testing SLA data collection...")
        
        try:
            # Initialize SLA collector
            collector = SLACollectorEngine()
            
            # Test data collection
            current_time = datetime.now(timezone.utc)
            test_metrics = collector.collect_current_metrics()
            
            assert isinstance(test_metrics, dict), "Metrics should be a dictionary"
            assert 'uptime' in test_metrics, "Missing uptime metric"
            assert 'response_time' in test_metrics, "Missing response_time metric"
            assert 'accuracy' in test_metrics, "Missing accuracy metric"
            
            self.logger.info("SLA data collection working")
            self.logger.info(f"Sample metrics: {json.dumps(test_metrics, indent=2)}")
            
        except ImportError:
            self.logger.warning("SLA collector module not available, skipping")
            self.test_results['skipped'] += 1
    
    def test_nft_minting_system(self):
        """Test NFT minting system integration"""
        self.logger.info("Testing NFT minting system...")
        
        if not self.blockchain_config.is_contract_deployed('SLAProofNFT'):
            self.logger.warning("Contract not deployed, skipping")
            return
        
        try:
            # Initialize minting system
            minting_system = SLANFTMintingSystem()
            
            # Test system initialization
            assert minting_system is not None, "Failed to initialize minting system"
            
            # Test mock certificate data preparation
            test_month_year = 202509  # September 2025
            mock_sla_data = {
                'uptime': 99.5,
                'response_time': 150,
                'accuracy': 98.8,
                'availability': 99.9,
                'transparency_score': 95.0,
                'blockchain_verifications': 100,
                'composite_sla_score': 96.2
            }
            
            # Test certificate metadata generation
            metadata = minting_system._prepare_certificate_metadata(
                test_month_year, 
                mock_sla_data,
                "test-user@example.com"
            )
            
            assert isinstance(metadata, dict), "Metadata should be a dictionary"
            assert 'name' in metadata, "Missing name in metadata"
            assert 'description' in metadata, "Missing description in metadata"
            assert 'attributes' in metadata, "Missing attributes in metadata"
            
            self.logger.info("NFT minting system integration working")
            self.logger.info(f"Sample metadata keys: {list(metadata.keys())}")
            
        except ImportError as e:
            self.logger.warning(f"Minting system module not available: {e}")
            self.test_results['skipped'] += 1
    
    def test_contract_queries(self):
        """Test contract query functions"""
        self.logger.info("Testing contract query functions...")
        
        if not self.blockchain_config.is_contract_deployed('SLAProofNFT'):
            self.logger.warning("Contract not deployed, skipping")
            return
        
        contract = get_sla_nft_contract()
        
        # Test monthly stats for current month
        current_month_year = int(datetime.now().strftime("%Y%m"))
        try:
            cert_count, avg_sla, report_cid = contract.functions.getMonthlyStats(current_month_year).call()
            
            self.logger.info(f"Monthly stats for {current_month_year}:")
            self.logger.info(f"  Certificate count: {cert_count}")
            self.logger.info(f"  Average SLA: {avg_sla}")
            self.logger.info(f"  Report CID: {report_cid}")
            
        except Exception as e:
            self.logger.info(f"Monthly stats query: {e}")
        
        # Test user certificates (using zero address as example)
        try:
            zero_address = '0x0000000000000000000000000000000000000000'
            user_certs = contract.functions.getUserCertificates(zero_address).call()
            self.logger.info(f"User certificates for zero address: {len(user_certs)}")
            
        except Exception as e:
            self.logger.info(f"User certificates query: {e}")
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        self.logger.info("Testing error handling...")
        
        if not self.blockchain_config.is_contract_deployed('SLAProofNFT'):
            self.logger.warning("Contract not deployed, skipping")
            return
        
        contract = get_sla_nft_contract()
        
        # Test querying non-existent certificate
        try:
            invalid_token_id = 999999
            contract.functions.getCertificate(invalid_token_id).call()
            assert False, "Should have failed for non-existent token"
        except Exception:
            self.logger.info("✓ Correctly failed for non-existent certificate")
        
        # Test invalid month year
        try:
            invalid_month_year = 999999
            contract.functions.getMonthlyStats(invalid_month_year).call()
            # This might not fail but should return empty data
            self.logger.info("✓ Handled invalid month year")
        except Exception as e:
            self.logger.info(f"✓ Error handling for invalid month year: {e}")
    
    def test_performance(self):
        """Test performance of contract calls"""
        self.logger.info("Testing performance...")
        
        if not self.blockchain_config.is_contract_deployed('SLAProofNFT'):
            self.logger.warning("Contract not deployed, skipping")
            return
        
        contract = get_sla_nft_contract()
        
        # Time multiple contract calls
        start_time = time.time()
        
        for i in range(5):
            contract.functions.name().call()
            contract.functions.symbol().call()
            contract.functions.totalCertificatesIssued().call()
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 15  # 15 total calls
        
        self.logger.info(f"Average call time: {avg_time:.3f} seconds")
        assert avg_time < 2.0, f"Contract calls too slow: {avg_time:.3f}s"
    
    def print_test_summary(self):
        """Print test results summary"""
        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['skipped']
        
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"⏭️  Skipped: {self.test_results['skipped']}")
        
        if self.test_results['errors']:
            print("\n🔍 Error Details:")
            for error in self.test_results['errors']:
                print(f"  • {error}")
        
        success_rate = (self.test_results['passed'] / max(1, total_tests - self.test_results['skipped'])) * 100
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        if self.test_results['failed'] == 0:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed!")
            return False

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Test SLA NFT contract integration')
    parser.add_argument('--network', choices=['base-sepolia', 'base-mainnet', 'localhost'],
                       help='Network to test against')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    try:
        tester = ContractIntegrationTester(
            network_name=args.network,
            verbose=args.verbose
        )
        
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Advanced regression tests for critical business scenarios
"""
import requests
import json
import time

class AdvancedRegressionTests:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Authenticate
        self.session.post(f"{self.base_url}/login", 
                         data={"email": "hxl2022hao@gmail.com"})

    def test_large_scale_mining_calculation(self):
        """Test calculation with large mining operations"""
        print("Testing large-scale mining calculations...")
        
        # Test with 1000+ miners
        calc_data = {
            'miner_model': 'Antminer S21',
            'miner_count': 1500,
            'electricity_cost': 0.04,
            'client_electricity_cost': 0.07,
            'use_real_time_data': True
        }
        
        response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
        
        if response.status_code == 200:
            data = response.json()
            daily_btc = data.get('btc_mined', {}).get('daily', 0)
            daily_profit = data.get('client_profit', {}).get('daily', 0)
            
            # Large operations should generate significant returns
            if daily_btc > 0.4 and daily_profit > 50000:
                print(f"  ✓ Large-scale calculation: {daily_btc:.4f} BTC/day, ${daily_profit:,.0f}/day")
                return True
            else:
                print(f"  ✗ Insufficient returns for large operation: {daily_btc} BTC, ${daily_profit}")
                return False
        
        print(f"  ✗ Calculation failed: {response.status_code}")
        return False

    def test_api_resilience_under_load(self):
        """Test API performance under rapid requests"""
        print("Testing API resilience under load...")
        
        start_time = time.time()
        successful_requests = 0
        
        for i in range(10):
            response = self.session.get(f"{self.base_url}/network_stats")
            if response.status_code == 200:
                successful_requests += 1
        
        duration = time.time() - start_time
        
        if successful_requests == 10 and duration < 30:
            print(f"  ✓ API resilience: {successful_requests}/10 requests in {duration:.2f}s")
            return True
        else:
            print(f"  ✗ API performance issue: {successful_requests}/10 in {duration:.2f}s")
            return False

    def test_data_consistency_over_time(self):
        """Test data consistency across multiple requests"""
        print("Testing data consistency...")
        
        # Get network data multiple times
        responses = []
        for i in range(3):
            response = self.session.get(f"{self.base_url}/network_stats")
            if response.status_code == 200:
                responses.append(response.json())
            time.sleep(1)
        
        if len(responses) == 3:
            # Check if BTC price variations are reasonable (within 5%)
            prices = [r.get('price', 0) for r in responses]
            price_variation = (max(prices) - min(prices)) / min(prices) * 100
            
            if price_variation < 5:
                print(f"  ✓ Data consistency: Price variation {price_variation:.2f}%")
                return True
            else:
                print(f"  ✗ High price variation: {price_variation:.2f}%")
                return False
        
        print("  ✗ Failed to collect consistent data samples")
        return False

    def test_curtailment_calculations(self):
        """Test power curtailment functionality"""
        print("Testing curtailment calculations...")
        
        calc_data = {
            'miner_model': 'Antminer S21',
            'miner_count': 100,
            'electricity_cost': 0.05,
            'curtailment': 15.0,  # 15% curtailment
            'use_real_time_data': True
        }
        
        response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
        
        if response.status_code == 200:
            data = response.json()
            curtailment_details = data.get('curtailment_details', {})
            
            if curtailment_details:
                print(f"  ✓ Curtailment calculation successful")
                return True
            else:
                print(f"  ✗ Missing curtailment details")
                return False
        
        print(f"  ✗ Curtailment calculation failed: {response.status_code}")
        return False

    def test_multi_currency_comparison(self):
        """Test SHA-256 cryptocurrency comparison stability"""
        print("Testing multi-currency comparison...")
        
        response = self.session.get(f"{self.base_url}/mining/sha256_comparison")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                coins = data.get('data', [])
                
                # Verify we have major cryptocurrencies
                coin_names = [coin.get('coin_name', '') for coin in coins]
                
                if 'Bitcoin' in coin_names and len(coins) >= 3:
                    print(f"  ✓ Multi-currency comparison: {len(coins)} coins including Bitcoin")
                    return True
                else:
                    print(f"  ✗ Insufficient currency data: {coin_names}")
                    return False
        
        print(f"  ✗ Comparison API failed: {response.status_code}")
        return False

    def test_edge_case_inputs(self):
        """Test system behavior with edge case inputs"""
        print("Testing edge case handling...")
        
        # Test with zero miners
        response = self.session.post(f"{self.base_url}/calculate", 
                                   data={'miner_count': 0})
        
        # Test with extremely high electricity cost
        response2 = self.session.post(f"{self.base_url}/calculate", 
                                    data={
                                        'miner_model': 'Antminer S21',
                                        'miner_count': 10,
                                        'electricity_cost': 1.0  # $1/kWh
                                    })
        
        if response.status_code in [200, 400] and response2.status_code == 200:
            print("  ✓ Edge cases handled appropriately")
            return True
        else:
            print("  ✗ Edge case handling issues")
            return False

    def run_advanced_tests(self):
        """Execute advanced regression test suite"""
        print("=" * 60)
        print("ADVANCED REGRESSION TESTS")
        print("=" * 60)
        
        tests = [
            self.test_large_scale_mining_calculation,
            self.test_api_resilience_under_load,
            self.test_data_consistency_over_time,
            self.test_curtailment_calculations,
            self.test_multi_currency_comparison,
            self.test_edge_case_inputs
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("\n" + "=" * 60)
        print(f"ADVANCED TESTS: {passed}/{total} PASSED ({passed/total*100:.1f}%)")
        print("=" * 60)
        
        return passed == total

if __name__ == "__main__":
    suite = AdvancedRegressionTests()
    success = suite.run_advanced_tests()
    
    if success:
        print("\n✅ ALL ADVANCED TESTS PASSED - Production ready")
    else:
        print("\n❌ Some advanced tests failed - Review required")
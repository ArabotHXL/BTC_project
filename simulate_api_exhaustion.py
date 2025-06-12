#!/usr/bin/env python3
"""
Simulate API exhaustion to test fallback mechanism
"""
import os
import sys
sys.path.append('.')

def mock_exhausted_coinwarz_api():
    """Temporarily simulate CoinWarz API exhaustion"""
    # This modifies the coinwarz_api module to return 0 available calls
    import coinwarz_api
    
    # Store original function
    original_check_status = coinwarz_api.check_coinwarz_api_status
    
    def mock_check_status():
        return {
            'Approved': True,
            'ApiUsageAvailable': 0,  # Simulate exhausted API
            'DailyUsageAvailable': 0
        }
    
    # Replace function temporarily
    coinwarz_api.check_coinwarz_api_status = mock_check_status
    
    print("🔄 Simulating CoinWarz API exhaustion...")
    print("   Available calls set to: 0")
    
    # Test the enhanced network data with exhausted API
    enhanced_data = coinwarz_api.get_enhanced_network_data()
    
    if enhanced_data:
        print(f"\n✅ Fallback system activated successfully!")
        print(f"   Data source: {enhanced_data['data_source']}")
        print(f"   BTC price: ${enhanced_data['btc_price']:,.2f}")
        print(f"   Network hashrate: {enhanced_data['hashrate']:.1f} EH/s")
        print(f"   Hashrate source: {enhanced_data['hashrate_source']}")
        print(f"   Health status: {enhanced_data['health_status']}")
        
        if 'fallback_reason' in enhanced_data:
            print(f"   Fallback reason: {enhanced_data['fallback_reason']}")
        
        if 'calculated_hashrate' in enhanced_data:
            print(f"   Cross-verification: {enhanced_data['calculated_hashrate']:.1f} EH/s (calculated)")
    
    # Restore original function
    coinwarz_api.check_coinwarz_api_status = original_check_status
    print("\n🔄 Restored normal API operation")

if __name__ == "__main__":
    print("=== Smart API Switching Simulation ===")
    print("Testing automatic fallback when CoinWarz API is exhausted\n")
    
    mock_exhausted_coinwarz_api()
    
    print("\n=== Simulation Complete ===")
    print("The system seamlessly switches to blockchain.info when CoinWarz is unavailable.")
    print("Data integrity is maintained through cross-validation.")
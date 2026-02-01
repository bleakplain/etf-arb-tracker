#!/usr/bin/env python3
"""
Comprehensive E2E Test Script for Backtest Wizard

Tests the backtest wizard functionality using API calls and HTML validation
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = f"{BASE_URL}/frontend/index.html"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_section(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}═{msg}═{Colors.END}")
    print()

def test_api_status():
    """Test 1: API Status Endpoint"""
    print_section("Test 1: API Status")

    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"API Status endpoint OK (200)")
            print_info(f"Is trading time: {data.get('is_trading_time')}")
            return True
        else:
            print_error(f"API Status returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"API Status failed: {e}")
        return False

def test_strategy_templates_api():
    """Test 2: Strategy Templates API"""
    print_section("Test 2: Strategy Templates API")

    try:
        response = requests.get(f"{BASE_URL}/api/backtest/templates", timeout=10)
        if response.status_code == 200:
            data = response.json()
            templates = data.get('templates', [])

            if len(templates) == 3:
                print_success(f"Retrieved {len(templates)} templates")

                for template in templates:
                    print_info(f"  - {template['name']}: min_weight={template['min_weight']*100}%, "
                            f"min_volume={template['min_etf_volume']}万")

                # Verify conservative template
                conservative = next(t for t in templates if t['id'] == 'conservative')
                if conservative['min_weight'] == 0.08 and conservative['min_etf_volume'] == 8000:
                    print_success("Conservative template values correct")

                # Verify balanced template
                balanced = next(t for t in templates if t['id'] == 'balanced')
                if balanced['min_weight'] == 0.05 and balanced['min_etf_volume'] == 5000:
                    print_success("Balanced template values correct")

                # Verify aggressive template
                aggressive = next(t for t in templates if t['id'] == 'aggressive')
                if aggressive['min_weight'] == 0.03 and aggressive['min_etf_volume'] == 3000:
                    print_success("Aggressive template values correct")

                return True
            else:
                print_error(f"Expected 3 templates, got {len(templates)}")
                return False
        else:
            print_error(f"Templates API returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Templates API failed: {e}")
        return False

def test_backtest_start_api():
    """Test 3: Start Backtest API"""
    print_section("Test 3: Start Backtest API")

    # Calculate date range (past 1 month)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    print_info(f"Testing with date range: {start_str} to {end_str}")

    payload = {
        "start_date": start_str,
        "end_date": end_str,
        "granularity": "daily",
        "min_weight": 0.05,
        "evaluator_type": "default",
        "interpolation": "linear"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/backtest/start",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            backtest_id = data.get('backtest_id')

            if backtest_id:
                print_success(f"Backtest started successfully")
                print_info(f"Backtest ID: {backtest_id}")
                return backtest_id
            else:
                print_error("No backtest_id in response")
                return None
        else:
            print_error(f"Start backtest returned {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print_error(f"Start backtest failed: {e}")
        return None

def test_backtest_status(backtest_id):
    """Test 4: Check Backtest Status"""
    print_section("Test 4: Backtest Status")

    if not backtest_id:
        print_error("No backtest_id to check")
        return False

    try:
        response = requests.get(
            f"{BASE_URL}/api/backtest/{backtest_id}",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            progress = data.get('progress', 0)

            print_success(f"Backtest status: {status}")
            print_info(f"Progress: {progress*100:.1f}%")
            print_info(f"Message: {data.get('message', 'N/A')}")

            if status in ['queued', 'running', 'completed', 'failed']:
                print_success("Status is valid")
                return True
            else:
                print_error(f"Unknown status: {status}")
                return False
        else:
            print_error(f"Status check returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Status check failed: {e}")
        return False

def test_backtest_list():
    """Test 5: List Backtests"""
    print_section("Test 5: List Backtests")

    try:
        response = requests.get(f"{BASE_URL}/api/backtest", timeout=10)

        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])

            print_success(f"Retrieved {len(jobs)} backtest jobs")

            for job in jobs[:3]:  # Show first 3
                job_id = job.get('job_id', 'N/A')[:8]
                status = job.get('status', 'N/A')
                print_info(f"  - Job {job_id}: {status}")

            return True
        else:
            print_error(f"List backtests returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"List backtests failed: {e}")
        return False

def test_frontend_html_structure():
    """Test 6: Frontend HTML Structure"""
    print_section("Test 6: Frontend HTML Structure")

    try:
        response = requests.get(FRONTEND_URL, timeout=10)

        if response.status_code == 200:
            html = response.text

            # Check for key elements
            checks = [
                ('Backtest tab', 'id="backtest"'),
                ('Wizard progress', 'class="wizard-progress"'),
                ('Step 1 panel', 'id="wizard-step-1"'),
                ('Step 2 panel', 'id="wizard-step-2"'),
                ('Step 3 panel', 'id="wizard-step-3"'),
                ('Step 4 panel', 'id="wizard-step-4"'),
                ('Strategy templates container', 'id="strategy-templates"'),
                ('Start date input', 'id="wizard-start-date"'),
                ('End date input', 'id="wizard-end-date"'),
                ('Next button', 'id="wizard-next-btn"'),
                ('Start button', 'id="wizard-start-btn"'),
                ('Wizard CSS', 'css/backtest-wizard.css'),
                ('Wizard JS', 'js/backtest-wizard.js'),
            ]

            passed = 0
            for name, selector in checks:
                if selector in html:
                    print_success(f"{name}: found")
                    passed += 1
                else:
                    print_error(f"{name}: NOT found")

            print_info(f"HTML structure: {passed}/{len(checks)} checks passed")
            return passed == len(checks)
        else:
            print_error(f"Frontend returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Frontend check failed: {e}")
        return False

def test_flatpickr_integration():
    """Test 7: Flatpickr Date Picker Integration"""
    print_section("Test 7: Flatpickr Integration")

    try:
        response = requests.get(FRONTEND_URL, timeout=10)

        if response.status_code == 200:
            html = response.text

            # Check for flatpickr resources
            checks = [
                ('Flatpickr CSS', 'flatpickr.min.css'),
                ('Flatpickr JS', 'flatpickr'),
                ('Chinese locale', 'zh.js'),
            ]

            passed = 0
            for name, resource in checks:
                if resource in html:
                    print_success(f"{name}: found")
                    passed += 1
                else:
                    print_info(f"{name}: not found (may be CDN)")

            # Check for date picker icon
            if 'bi-calendar3' in html:
                print_success("Date picker icon: found")
                passed += 1
            else:
                print_error("Date picker icon: NOT found")

            # Check for readonly date inputs
            if 'readonly' in html and 'wizard-start-date' in html:
                print_success("Date inputs are readonly (using flatpickr)")
                passed += 1
            else:
                print_error("Date inputs should be readonly")

            print_info(f"Flatpickr integration: {passed}/{len(checks)+2} checks passed")
            return passed >= 2
        else:
            print_error(f"Frontend returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Flatpickr check failed: {e}")
        return False

def generate_test_report(results):
    """Generate Test Report"""
    print_section("Test Report Summary")

    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed

    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
    print(f"{Colors.RED}Failed: {failed}{Colors.END}")

    if passed == total:
        print(f"\n{Colors.BOLD}{Colors.GREEN}All tests passed! 🎉{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}Some tests failed!{Colors.END}\n")
        return 1

def main():
    """Run all E2E tests"""
    print(f"{Colors.BOLD}{Colors.BLUE}╔══════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}║   Backtest Wizard E2E Test Suite      ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}╚══════════════════════════════════════╝{Colors.END}")
    print()
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Frontend URL: {FRONTEND_URL}")
    print_info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []
    backtest_id = None

    # Run tests
    results.append({
        'name': 'API Status',
        'passed': test_api_status()
    })

    results.append({
        'name': 'Strategy Templates API',
        'passed': test_strategy_templates_api()
    })

    results.append({
        'name': 'Frontend HTML Structure',
        'passed': test_frontend_html_structure()
    })

    results.append({
        'name': 'Flatpickr Integration',
        'passed': test_flatpickr_integration()
    })

    results.append({
        'name': 'List Backtests',
        'passed': test_backtest_list()
    })

    # Start a backtest and check status
    backtest_id = test_backtest_start_api()
    if backtest_id:
        results.append({
            'name': 'Start Backtest API',
            'passed': True
        })

        results.append({
            'name': 'Backtest Status',
            'passed': test_backtest_status(backtest_id)
        })
    else:
        results.append({
            'name': 'Start Backtest API',
            'passed': False
        })
        results.append({
            'name': 'Backtest Status',
            'passed': False
        })

    # Generate report
    exit_code = generate_test_report(results)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

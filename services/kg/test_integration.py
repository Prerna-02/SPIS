"""
=============================================================================
Integration Tests - CP-SAT Optimizer + API + Cascade
=============================================================================

Test suite for Feature 4 Phase 4 integration:
1. Optimizer with mixed WAITING + APPROACHING vessels
2. Cascade reason formatting correctness
3. Missing ETA handling
4. Fallback plan generation

Run:
    cd e:\DL_Final_Project\services\kg
    python test_integration.py
=============================================================================
"""

import sys
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_optimizer_with_mixed_vessels():
    """Test optimizer with WAITING + APPROACHING vessels."""
    print("\n" + "="*60)
    print("TEST 1: Optimizer with mixed WAITING + APPROACHING vessels")
    print("="*60)
    
    from optimizer import optimize_scenario, VesselData, BerthData
    
    # Simulate vessels from KG
    vessels = [
        {"mmsi": "V001", "status": "WAITING", "eta_to_port": "0.0 hours"},
        {"mmsi": "V002", "status": "WAITING", "eta_to_port": "1.0 hours"},
        {"mmsi": "V003", "status": "APPROACHING", "eta_to_port": "3.0 hours"},
        {"mmsi": "V004", "status": "APPROACHING", "eta_to_port": "26.0 hours"},  # Beyond 24h
    ]
    
    berths = [
        {"berth_id": "B1", "terminal": "OLD_CITY", "service_rate_base": 30.0, "crane_count": 2},
        {"berth_id": "B2", "terminal": "MUUGA", "service_rate_base": 40.0, "crane_count": 3},
    ]
    
    extra_vessel = {
        "mmsi": "EXTRA_001",
        "eta": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "containers_est": 200,
        "cargo_priority": "pharma",
    }
    
    plans = optimize_scenario(vessels, berths, extra_vessel)
    
    assert len(plans) > 0, "Expected at least one plan"
    plan = plans[0]
    
    print(f"✅ Generated {len(plans)} plan(s)")
    print(f"   Plan ID: {plan.plan_id}")
    print(f"   Objective Score: {plan.objective_score}")
    print(f"   Total Delay: {plan.total_delay_hours} hours")
    print(f"   Vessels Impacted: {plan.vessels_impacted}")
    print(f"   Assignments: {len(plan.assignments)}")
    
    # Verify V004 (beyond 24h horizon) was excluded
    vessel_mmsis = {a.vessel_mmsi for a in plan.assignments}
    assert "V004" not in vessel_mmsis, "V004 should be excluded (beyond 24h horizon)"
    print("✅ V004 correctly excluded (ETA beyond 24h horizon)")
    
    return True


def test_cascade_reason_formatting():
    """Test cascade reason includes berth context."""
    print("\n" + "="*60)
    print("TEST 2: Cascade reason formatting")
    print("="*60)
    
    from optimizer import BerthOptimizer, VesselData, BerthData
    
    vessels = [
        VesselData(mmsi="V001", eta_minutes=0, containers=200, priority_score=1),
        VesselData(mmsi="V002", eta_minutes=30, containers=150, priority_score=2),
        VesselData(mmsi="EXTRA", eta_minutes=60, containers=300, priority_score=4, is_extra=True),
    ]
    
    berths = [
        BerthData(berth_id="B1", terminal="OLD_CITY", service_rate=30, crane_count=2),
    ]
    
    optimizer = BerthOptimizer(vessels, berths)
    optimizer.build_model()
    plan = optimizer.solve()
    
    assert plan is not None, "Expected a plan"
    
    print(f"✅ Plan generated: {plan.plan_id}")
    print(f"   Cascade impacts: {len(plan.impacts)}")
    
    # Check reason formatting
    for impact in plan.impacts:
        print(f"   Impact: {impact.vessel_mmsi}")
        print(f"   Reason: {impact.reason}")
        assert "Berth" in impact.reason or "congested" in impact.reason, \
            "Reason should include berth context"
    
    print("✅ Cascade reasons include berth context")
    return True


def test_missing_eta_handling():
    """Test handling of missing ETA for APPROACHING vessels."""
    print("\n" + "="*60)
    print("TEST 3: Missing ETA handling")
    print("="*60)
    
    from optimizer import optimize_scenario
    
    # Simulate vessels with missing ETA
    vessels = [
        {"mmsi": "V001", "status": "WAITING", "eta_to_port": None},  # WAITING with no ETA
        {"mmsi": "V002", "status": "APPROACHING", "eta_to_port": None},  # APPROACHING with no ETA
        {"mmsi": "V003", "status": "APPROACHING", "eta_to_port": "2.0 hours"},
    ]
    
    berths = [
        {"berth_id": "B1", "terminal": "OLD_CITY", "service_rate_base": 30.0, "crane_count": 2},
    ]
    
    extra_vessel = {
        "eta": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "containers_est": 100,
        "cargo_priority": "general",
    }
    
    plans = optimize_scenario(vessels, berths, extra_vessel)
    
    assert len(plans) > 0, "Expected at least one plan"
    plan = plans[0]
    
    vessel_mmsis = {a.vessel_mmsi for a in plan.assignments}
    
    # WAITING vessels should be included even with missing ETA
    assert "V001" in vessel_mmsis, "V001 (WAITING) should be included despite missing ETA"
    print("✅ V001 (WAITING) included despite missing ETA")
    
    # APPROACHING vessels with missing ETA should be excluded
    assert "V002" not in vessel_mmsis, "V002 (APPROACHING) should be excluded due to missing ETA"
    print("✅ V002 (APPROACHING) excluded due to missing ETA")
    
    # APPROACHING vessels with valid ETA should be included
    assert "V003" in vessel_mmsis, "V003 (APPROACHING with valid ETA) should be included"
    print("✅ V003 (APPROACHING with valid ETA) included")
    
    return True


def test_fallback_plan():
    """Test fallback plan generation when no feasible solution exists."""
    print("\n" + "="*60)
    print("TEST 4: Fallback plan generation")
    print("="*60)
    
    from optimizer import create_fallback_plan, VesselData, BerthData
    
    # Create an extreme scenario
    vessels = [VesselData(mmsi=f"V{i:03d}", eta_minutes=0, containers=500) for i in range(10)]
    berths = [BerthData(berth_id="B1", terminal="OLD_CITY", service_rate=1, crane_count=1)]
    extra_vessel = VesselData(mmsi="EXTRA", eta_minutes=60, containers=500, is_extra=True)
    
    fallback = create_fallback_plan(vessels, berths, extra_vessel)
    
    assert fallback is not None, "Expected fallback plan"
    assert fallback.plan_id == "fallback_plan"
    assert len(fallback.impacts) > 0, "Fallback should have at least one impact"
    
    impact = fallback.impacts[0]
    assert "No feasible" in impact.reason or "Recommendation" in impact.reason, \
        "Fallback reason should explain the situation"
    
    print(f"✅ Fallback plan generated: {fallback.plan_id}")
    print(f"   Delay: {fallback.total_delay_hours} hours")
    print(f"   Reason: {impact.reason[:80]}...")
    
    return True


def run_all_tests():
    """Run all integration tests."""
    print("="*60)
    print("INTEGRATION TESTS - CP-SAT + API + Cascade")
    print("="*60)
    
    results = []
    
    try:
        results.append(("Mixed Vessels", test_optimizer_with_mixed_vessels()))
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        results.append(("Mixed Vessels", False))
    
    try:
        results.append(("Cascade Formatting", test_cascade_reason_formatting()))
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        results.append(("Cascade Formatting", False))
    
    try:
        results.append(("Missing ETA", test_missing_eta_handling()))
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        results.append(("Missing ETA", False))
    
    try:
        results.append(("Fallback Plan", test_fallback_plan()))
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        results.append(("Fallback Plan", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

package ledger

// VerifyChainWindow checks whether trailing event digests satisfy the competence floor.
func VerifyChainWindow(scores []float64, floor float64, minCount int) bool {
	if len(scores) < minCount {
		return false
	}
	breaches := 0
	for i := 0; i < len(scores); i++ {
		if scores[i] < floor {
			breaches++
		}
	}
	return breaches == 0
}

// ClampQuotaWindow bounds token allocation within [minQuota, maxQuota].
func ClampQuotaWindow(requested int, minQuota int, maxQuota int) int {
	if requested < minQuota {
		return minQuota
	}
	if requested > maxQuota {
		return maxQuota
	}
	return requested
}

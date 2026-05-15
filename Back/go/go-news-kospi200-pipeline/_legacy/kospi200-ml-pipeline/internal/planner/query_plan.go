package planner

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

type QueryJob struct {
	JobID          string `json:"job_id"`
	JobType        string `json:"job_type"`
	Ticker         string `json:"ticker"`
	CompanyNameKO  string `json:"company_name_ko"`
	Market         string `json:"market"`
	Priority       int    `json:"priority"`
	Query          string `json:"query"`
	QuerySource    string `json:"query_source"`
	QueryRank      int    `json:"query_rank"`
	QueryGroupSize int    `json:"query_group_size"`
	MaxResultsHint int    `json:"max_results_hint"`
	UsedForML      bool   `json:"used_for_ml"`
	UsedForDigest  bool   `json:"used_for_digest"`
}

type QueryPlanStats struct {
	CompanyCount         int `json:"company_count"`
	CompanyJobCount      int `json:"company_job_count"`
	MacroJobCount        int `json:"macro_job_count"`
	TotalJobCount        int `json:"total_job_count"`
	MaxQueriesPerCompany int `json:"max_queries_per_company"`
}

type QueryPlan struct {
	PlanName    string         `json:"plan_name"`
	AsOfDate    string         `json:"as_of_date"`
	GeneratedAt string         `json:"generated_at"`
	SourceFiles map[string]any `json:"source_files"`
	Stats       QueryPlanStats `json:"stats"`
	Jobs        []QueryJob     `json:"jobs"`
}

func Load(path string) (QueryPlan, error) {
	var plan QueryPlan

	b, err := os.ReadFile(path)
	if err != nil {
		return plan, err
	}
	if err := json.Unmarshal(b, &plan); err != nil {
		return plan, err
	}
	if len(plan.Jobs) == 0 {
		return plan, fmt.Errorf("query plan has no jobs: %s", path)
	}

	sort.SliceStable(plan.Jobs, func(i, j int) bool {
		if plan.Jobs[i].Priority == plan.Jobs[j].Priority {
			if plan.Jobs[i].JobType == plan.Jobs[j].JobType {
				return plan.Jobs[i].JobID < plan.Jobs[j].JobID
			}
			return plan.Jobs[i].JobType < plan.Jobs[j].JobType
		}
		return plan.Jobs[i].Priority > plan.Jobs[j].Priority
	})

	return plan, nil
}

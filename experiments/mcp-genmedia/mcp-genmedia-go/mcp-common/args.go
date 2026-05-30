// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package common

import (
	"fmt"
	"math"
)

// ParseOptionalNonNegativeInt32 extracts an optional integer MCP argument.
func ParseOptionalNonNegativeInt32(args map[string]interface{}, name string) (*int32, error) {
	value, ok := args[name]
	if !ok || value == nil {
		return nil, nil
	}

	var parsed int64
	switch v := value.(type) {
	case float64:
		if math.Trunc(v) != v {
			return nil, fmt.Errorf("%s must be an integer", name)
		}
		parsed = int64(v)
	case float32:
		if math.Trunc(float64(v)) != float64(v) {
			return nil, fmt.Errorf("%s must be an integer", name)
		}
		parsed = int64(v)
	case int:
		parsed = int64(v)
	case int32:
		parsed = int64(v)
	case int64:
		parsed = v
	default:
		return nil, fmt.Errorf("%s must be a number", name)
	}

	if parsed < 0 || parsed > math.MaxInt32 {
		return nil, fmt.Errorf("%s must be between 0 and %d", name, math.MaxInt32)
	}

	result := int32(parsed)
	return &result, nil
}

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

import "testing"

func TestParseOptionalNonNegativeInt32(t *testing.T) {
	tests := []struct {
		name    string
		args    map[string]interface{}
		want    *int32
		wantErr bool
	}{
		{
			name: "missing",
			args: map[string]interface{}{},
		},
		{
			name: "float64 integer",
			args: map[string]interface{}{"seed": float64(42)},
			want: int32Ptr(42),
		},
		{
			name: "int",
			args: map[string]interface{}{"seed": 7},
			want: int32Ptr(7),
		},
		{
			name:    "fractional",
			args:    map[string]interface{}{"seed": float64(1.5)},
			wantErr: true,
		},
		{
			name:    "negative",
			args:    map[string]interface{}{"seed": -1},
			wantErr: true,
		},
		{
			name:    "too large",
			args:    map[string]interface{}{"seed": int64(2147483648)},
			wantErr: true,
		},
		{
			name:    "not numeric",
			args:    map[string]interface{}{"seed": "42"},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseOptionalNonNegativeInt32(tt.args, "seed")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tt.want == nil {
				if got != nil {
					t.Fatalf("expected nil, got %d", *got)
				}
				return
			}
			if got == nil || *got != *tt.want {
				t.Fatalf("expected %d, got %v", *tt.want, got)
			}
		})
	}
}

func int32Ptr(v int32) *int32 {
	return &v
}

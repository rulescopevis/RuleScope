import {
  FetchedColumnTypes,
  validRange_Equality_Equality,
  invalidRange_Equality_Range,
  RefineResult,
  SelectInfo,
} from "@/types/types";
import axios from "axios";

export const api = axios.create({
  baseURL: "",
});

const API_BASE_URL = "/api/";

interface RangeValue {
  start?: number;
  end?: number;
  startInclusive?: boolean;
  endInclusive?: boolean;
}

export interface FormattedRule {
  [columnName: string]: string[] | RangeValue[];
}

interface DetectMultipleLogicConditionResponse {
  invalid_indices: any[];
  formatted_rules: any[];
}

export async function api_load_table_vis_valueList(
  column_name: string
): Promise<
  {
    value: string;
    count: number;
    countRate: number;
    index: number[];
    duration: string;
  }[]
> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}load_table_vis_valueList`,
      {
        column_name: column_name,
      }
    );
    return response.data.valueList || [];
  } catch (error) {
    console.error("Error load column data:", error);
    throw error;
  }
}

// load character data
export async function api_load_column_data(
  column_name: string
): Promise<{ value: string; count: number; countRate: number }[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}load_column_data`, {
      column_name: column_name,
    });
    return response.data.valueList || [];
  } catch (error) {
    console.error("Error load column data:", error);
    return [];
  }
}

export async function api_get_constraint_map() {
  try {
    const response = await axios.get(`${API_BASE_URL}get_constraint_map`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch constraint map:", error);
    throw error;
  }
}

export async function api_download_validation_rules(): Promise<{
  fileName: string;
  content: string;
}> {
  const response = await fetch(`${API_BASE_URL}download_validation_rules`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Failed to download validation rules");
  }

  const contentDisposition = response.headers.get("Content-Disposition") || "";
  let fileName = "validation_rules.json";
  const match = contentDisposition.match(/filename\s*=\s*"?([^";]+)"?/i);
  if (match && match[1]) {
    fileName = match[1];
  }

  const content = await response.text();
  return { fileName, content };
}

export async function api_download_detect_functions(): Promise<{
  fileName: string;
  content: string;
}> {
  const response = await fetch(`${API_BASE_URL}download_detect_functions`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Failed to download detection script");
  }

  const contentDisposition = response.headers.get("Content-Disposition") || "";
  let fileName = "detect_functions.py";
  const match = contentDisposition.match(/filename\s*=\s*"?([^";]+)"?/i);
  if (match && match[1]) {
    fileName = match[1];
  }

  const content = await response.text();
  return { fileName, content };
}

export async function api_get_finalValidation() {
  try {
    const response = await axios.get(`${API_BASE_URL}get_finalValidation`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch the JSON file:", error);
    throw error;
  }
}

export async function api_get_new_finalValidation() {
  try {
    const response = await axios.get(`${API_BASE_URL}get_new_finalValidation`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch the JSON file:", error);
    throw error;
  }
}

export async function api_get_sort_conditions(column_name: string) {
  try {
    const response = await axios.post(`${API_BASE_URL}get_sort_conditions`, {
      column_name: column_name,
    });
    return response.data.sort_conditions;
  } catch (error) {
    console.error("Failed to fetch sort conditions:", error);
    throw error;
  }
}

export async function api_load_missing_duplicate_detect_flag(
  column_name: string
): Promise<{ missing_detect_flag: boolean; duplicate_detect_flag: boolean }> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}load_missing_duplicate_detect_flag`,
      {
        column_name: column_name,
      }
    );
    return {
      missing_detect_flag: response.data.missing_detect_flag,
      duplicate_detect_flag: response.data.duplicate_detect_flag,
    };
  } catch (error) {
    console.error("Error load missing duplicate flag:", error);
    return { missing_detect_flag: false, duplicate_detect_flag: false };
  }
}

export async function api_load_missing_duplicate_flag(
  column_name: string
): Promise<{ missing_flag: boolean; duplicate_flag: boolean }> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}load_missing_duplicate_flag`,
      {
        column_name: column_name,
      }
    );
    return {
      missing_flag: response.data.missing_flag,
      duplicate_flag: response.data.duplicate_flag,
    };
  } catch (error) {
    console.error("Error load missing duplicate flag:", error);
    return { missing_flag: false, duplicate_flag: false };
  }
}

export async function api_detectColumnType(
  rawData: Array<Record<string, string | number | undefined>>
): Promise<FetchedColumnTypes> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_column_types`, {
      rawData: rawData,
    });
    return response.data.columnTypes;
  } catch (error) {
    console.error("Error fetching column types from API: ", error);
    throw error;
  }
}

// character duplicate
export async function api_characterDuplicate(
  columnData: (string | number | undefined)[]
): Promise<{ duplicateStatus: boolean; duplicateFlag: boolean } | undefined> {
  try {
    const response = await axios.post(`${API_BASE_URL}character_duplicate`, {
      column_data: columnData,
    });
    return {
      duplicateStatus: response.data.duplicateStatus,
      duplicateFlag: response.data.duplicateFlag,
    };
  } catch (error) {
    console.error(
      "Error fetching character duplicate status from API: ",
      error
    );
    return undefined;
  }
}

// numeric order & duplicate
export async function api_numericOrderDuplicate(
  columnData: (string | number | undefined)[]
): Promise<
  | {
      duplicateStatus: boolean;
      duplicateFlag: boolean;
      orderStatus: boolean;
      orderType: string;
    }
  | undefined
> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}numeric_order_duplicate`,
      {
        column_data: columnData,
      }
    );
    return {
      duplicateStatus: response.data.duplicateStatus,
      duplicateFlag: response.data.duplicateFlag,
      orderStatus: response.data.orderStatus,
      orderType: response.data.orderType,
    };
  } catch (error) {
    console.error("Error fetching numeric duplicate status from API: ", error);
    return undefined;
  }
}

// character missing index
export async function api_charactermissing_index(
  columnName: string
): Promise<number[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}character_missing`, {
      columnName: columnName,
    });
    return response.data.missingIndices || [];
  } catch (error) {
    console.error("Error detecting character missing indices:", error);
    return [];
  }
}

// numeric missing index
export async function api_numericmissing_index(
  columnName: string
): Promise<number[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}numeric_missing`, {
      columnName: columnName,
    });
    return response.data.missingIndices || [];
  } catch (error) {
    console.error("Error detecting numeric missing indices:", error);
    return [];
  }
}

// duplicate index
export async function api_duplicate_index(
  columnData: (string | number | undefined)[]
): Promise<number[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_duplicate`, {
      column_data: columnData,
    });
    return response.data.duplicateIndices || [];
  } catch (error) {
    console.error("Error detecting duplicates:", error);
    return [];
  }
}

export async function api_detect_absolute_difference(
  column_name: string
): Promise<
  {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[]
> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_absolute_difference`,
      {
        column_name: column_name,
      }
    );
    return response.data.invalid_pairs || [];
  } catch (error) {
    console.error("Error detecting sequence:", error);
    return [];
  }
}

export async function api_detect_relative_difference(
  column_name: string
): Promise<
  {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[]
> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_relative_difference`,
      {
        column_name: column_name,
      }
    );
    return response.data.invalid_pairs || [];
  } catch (error) {
    console.error("Error detecting relative difference:", error);
    return [];
  }
}

// case3: detect sequence
export async function api_detect_sequence(column_name: string): Promise<
  {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[]
> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_sequence`, {
      column_name: column_name,
    });
    return response.data.invalid_pairs || [];
  } catch (error) {
    console.error("Error detecting sequence:", error);
    return [];
  }
}

// case3: detect sequence valid
export async function api_detect_sequence_valid(column_name: string): Promise<
  {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[]
> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_sequence_valid`, {
      column_name: column_name,
    });
    return response.data.valid_pairs || [];
  } catch (error) {
    console.error("Error detecting valid sequence:", error);
    return [];
  }
}

// NL panel entrypoint
export async function api_nlpanel_handle(payload: {
  naturalLanguage: string;
  ruleContext?: any;
  createRule?: any;
  previewOnly?: boolean;
}): Promise<any> {
  const response = await axios.post(`${API_BASE_URL}nlpanel`, payload);
  return response.data;
}

// case2: ball_y & ball_area invalid index
export async function api_detect_condition_logic_index(
  csvData: Array<Record<string, string | number | undefined>>,
  selectedColumns: string[]
): Promise<number[]> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_condition_logic_index`,
      {
        csvData: csvData,
        selectedColumns: selectedColumns,
      }
    );
    return response.data.invalid_indices || [];
  } catch (error) {
    console.error("Error detecting invalid sequence:", error);
    return [];
  }
}

// case2: ball_y & ball_area valid index
export async function api_detect_condition_logic_index_valid(
  csvData: Array<Record<string, string | number | undefined>>,
  selectedColumns: string[]
): Promise<number[]> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_condition_logic_index_valid`,
      {
        csvData: csvData,
        selectedColumns: selectedColumns,
      }
    );
    return response.data.valid_indices || [];
  } catch (error) {
    console.error("Error detecting valid sequence:", error);
    return [];
  }
}

// case: game_clock >= shot_clock
export async function api_detect_compare_numeric(
  selectedColumns: string[]
): Promise<number[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_compare_numeric`, {
      selectedColumns: selectedColumns,
    });
    return response.data.invalid_indices || [];
  } catch (error) {
    console.error("Error detecting invalid sequence:", error);
    return [];
  }
}

export async function api_detect_compare_numeric_valid(
  csvData: Array<Record<string, string | number | undefined>>,
  selectedColumns: string[]
): Promise<number[]> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_compare_numeric_valid`,
      {
        csvData: csvData,
        selectedColumns: selectedColumns,
      }
    );
    return response.data.valid_indices || [];
  } catch (error) {
    console.error("Error detecting valid sequence:", error);
    return [];
  }
}

export async function api_detect_compare_date(
  selectedColumns: string[]
): Promise<number[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_compare_date`, {
      selectedColumns,
    });
    return response.data.invalid_indices || [];
  } catch (error) {
    console.error("Error detecting date compare invalid indices:", error);
    return [];
  }
}

export async function api_detect_compare_date_valid(
  csvData: Array<Record<string, string | number | undefined>>,
  selectedColumns: string[]
): Promise<number[]> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_compare_date_valid`,
      {
        csvData,
        selectedColumns,
      }
    );
    return response.data.valid_indices || [];
  } catch (error) {
    console.error("Error detecting date compare valid indices:", error);
    return [];
  }
}

export async function api_json_numeric_range(
  selectedColumn: string,
  ruleType: "Range" | "Outlier" = "Range"
): Promise<{ start: number | null; end: number | null }> {
  try {
    const response = await axios.post(`${API_BASE_URL}json_numeric_range`, {
      selectedColumn: selectedColumn,
      ruleType,
    });
    const { start, end } = response.data;
    return { start, end };
  } catch (error) {
    console.error("Error fetching numeric range:", error);
    return { start: null, end: null };
  }
}

export async function api_detect_numeric_range(
  selectedColumn: string
): Promise<number[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_numeric_range`, {
      selectedColumn: selectedColumn,
    });
    return response.data.invalid_indices || [];
  } catch (error) {
    console.error("Error detecting numeric range invalid indices:", error);
    return [];
  }
}

export async function api_detect_outliers(
  selectedColumn: string
): Promise<number[]> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_outliers`, {
      selectedColumn: selectedColumn,
    });
    return response.data.invalid_indices || [];
  } catch (error) {
    console.error("Error detecting outliers:", error);
    return [];
  }
}

export async function api_extract_invalid_range(
  csvData: Array<Record<string, string | number | undefined>>,
  selectedColumns: string[]
): Promise<
  Array<invalidRange_Equality_Range> | Array<validRange_Equality_Equality>
> {
  try {
    const response = await axios.post(`${API_BASE_URL}extract_invalid_range`, {
      csvData: csvData,
      selectedColumns: selectedColumns,
    });

    if (response.status === 200) {
      return response.data;
    } else {
      throw new Error("Failed to fetch invalid start and end values");
    }
  } catch (error) {
    console.error("Error in api_extract_invalid_range_equality_range:", error);
    throw error;
  }
}

export async function api_extract_lookup_area(
  columnNames: string[]
): Promise<Array<validRange_Equality_Equality>> {
  const response = await axios.post(`${API_BASE_URL}extract_lookup_area`, {
    columnNames: columnNames,
  });
  return response.data.lookup_areas || [];
}

export async function api_sequence_invalid_range(
  column_name: string
): Promise<validRange_Equality_Equality[]> {
  const response = await axios.post(`${API_BASE_URL}sequence_invalid_range`, {
    column_name: column_name,
  });
  return response.data.invalid_range || [];
}

export async function api_invalid_pairs_to_indices(
  invalid_pairs: {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[]
): Promise<number[]> {
  const response = await axios.post(`${API_BASE_URL}invalid_pairs_to_indices`, {
    invalid_pairs: invalid_pairs,
  });
  return response.data.invalid_indices || [];
}

export async function api_invalid_pairs_to_sorted_indices(
  invalid_pairs: {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[]
): Promise<number[]> {
  const response = await axios.post(
    `${API_BASE_URL}invalid_pairs_to_sorted_indices`,
    {
      invalid_pairs: invalid_pairs,
    }
  );
  return response.data.sorted_indices || [];
}

export async function api_submit_text(
  inputText: string,
  columnNames: string[],
  ruleType: string,
  ruleValue: string
) {
  try {
    const response = await axios.post(`${API_BASE_URL}submit-text`, {
      text: inputText,
      columnNames: columnNames,
      ruleType: ruleType,
      ruleValue: ruleValue,
    });
    return response.data.result;
  } catch (error) {
    console.error("Error submitting text:", error);
  }
}

export async function api_detect_conflict_flag(
  invalid_indices: number[]
): Promise<number> {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_conflict_flag`, {
      invalid_indices: invalid_indices,
    });
    return response.data.conflict_flag;
  } catch (error) {
    console.error("Error detecting conflict flag:", error);
    return 0;
  }
}

export async function api_detect_multi_difference(
  columnNames: string[]
): Promise<
  {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[]
> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_multi_difference`,
      {
        columnNames: columnNames,
      }
    );
    return response.data.invalid_pairs || [];
  } catch (error) {
    console.error("Error detecting multi-dimensional difference:", error);
    return [];
  }
}

export async function api_refine_validation_rules(
  validFlag: boolean,
  selectInfo: SelectInfo
): Promise<RefineResult> {
  try {
    const response = await axios.post<RefineResult>(
      `${API_BASE_URL}refine_validation_rules`,
      {
        validFlag,
        selectInfo,
      },
      {
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        transformResponse: [
          (data) => {
            if (typeof data === "string") {
              try {
                return JSON.parse(data);
              } catch (e) {
                console.error("Failed to parse response:", e);
                return data;
              }
            }
            return data;
          },
        ],
      }
    );
    return response.data;
  } catch (error) {
    console.error("Error refining validation rules:", error);
    return {
      refineStatus: false,
      refineDict: {
        addRules: [],
        deleteRules: [],
        updateRules: [],
      },
    };
  }
}

export async function api_get_multi_difference_sort_conditions(
  columnNames: string[]
) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}get_multi_difference_sort_conditions`,
      {
        columnNames: columnNames,
      }
    );
    return response.data.sort_conditions;
  } catch (error) {
    console.error("Failed to fetch multi difference sort conditions:", error);
    throw error;
  }
}

export async function api_get_refine_rules(rules: any) {
  try {
    const response = await fetch(`${API_BASE_URL}get_refine_rules`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(rules),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error updating rules:", error);
    throw error;
  }
}

export async function api_detect_multiple_duplicate(columnNames: string[]) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}detect_multiple_duplicate`,
      {
        columnNames: columnNames,
      }
    );
    return response.data.invalid_indices || [];
  } catch (error) {
    console.error("Error detecting multiple duplicate:", error);
    return [];
  }
}

export async function api_detect_lookup(columnNames: string[]) {
  try {
    const response = await axios.post(`${API_BASE_URL}detect_lookup`, {
      columnNames: columnNames,
    });

    return response.data.invalid_indices || [];
  } catch (error) {
    console.error("Error detecting lookup:", error);
    return [];
  }
}

export interface UploadDatasetResponse {
  dataset: string;
  displayName: string;
  message: string;
}

export interface ApiProviderConfig {
  apiKey: string;
  baseUrl: string;
  model: string;
}

export interface ApiConfigResponse {
  apiProvider: string;
  providers: Record<string, ApiProviderConfig>;
}

export async function api_change_dataset(
  dataset: string,
  workflowMode: string
): Promise<boolean> {
  try {
    const response = await axios.post(`${API_BASE_URL}change-dataset`, {
      dataset: dataset,
      workflowMode: workflowMode,
    });
    return response.status === 200;
  } catch (error) {
    console.error("Failed to change dataset:", error);
    throw error;
  }
}

export async function api_set_workflow_mode(
  workflowMode: string
): Promise<void> {
  try {
    await axios.post(`${API_BASE_URL}workflow-mode`, {
      workflowMode,
    });
  } catch (error) {
    console.error("Failed to update workflow mode:", error);
    throw error;
  }
}

export async function api_get_api_config(): Promise<ApiConfigResponse> {
  try {
    const response = await axios.get(`${API_BASE_URL}api-config`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch API config:", error);
    throw error;
  }
}

export async function api_save_api_config(payload: {
  apiProvider: string;
  apiKey: string;
  baseUrl?: string;
  model?: string;
}): Promise<ApiConfigResponse> {
  try {
    const response = await axios.post(`${API_BASE_URL}api-config`, payload);
    return response.data;
  } catch (error) {
    console.error("Failed to save API config:", error);
    throw error;
  }
}

export async function api_upload_dataset(
  file: File,
  workflowMode: string
): Promise<UploadDatasetResponse> {
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("workflowMode", workflowMode);

    const response = await axios.post(
      `${API_BASE_URL}upload-dataset`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    return response.data;
  } catch (error) {
    console.error("Failed to upload dataset:", error);
    throw error;
  }
}

export async function api_generate_card_example(
  columnName: string[],
  ruleType: string
): Promise<string> {
  try {
    const response = await axios.post(`${API_BASE_URL}generate_card_example`, {
      columnName: columnName,
      ruleType: ruleType,
    });
    return response.data.example;
  } catch (error) {
    console.error("Error generating card example:", error);
    return "";
  }
}

export async function api_get_current_csv_content(): Promise<string> {
  try {
    const response = await axios.get(`${API_BASE_URL}get_current_csv_content`);
    return response.data.csvContent;
  } catch (error) {
    console.error("Failed to fetch CSV content:", error);
    throw error;
  }
}

export async function api_detect_multiple_logic_condition(
  selectedColumns: string[]
): Promise<DetectMultipleLogicConditionResponse> {
  try {
    const response = await api.post("/api/detect_multiple_logic_condition", {
      selectedColumns,
    });
    return response.data;
  } catch (error) {
    console.error("Failed to detect multiple logic condition", error);
    return { invalid_indices: [], formatted_rules: [] };
  }
}

export async function api_get_rule_creation_info(): Promise<any> {
  try {
    const response = await api.get("/api/get_rule_creation_info");
    return response.data;
  } catch (error) {
    console.error("Failed to get rule creation info", error);
    return {};
  }
}

export async function api_create_rule(
  type: string,
  columns: string[],
  parameters: any
) {
  try {
    const response = await axios.post(`${API_BASE_URL}create-rule`, {
      type,
      columns,
      parameters,
    });
    return response.data;
  } catch (error) {
    console.error("Error creating rule:", error);
    throw error;
  }
}

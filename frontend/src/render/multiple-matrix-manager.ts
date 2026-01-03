import {
  Row,
  MatrixEventBus,
  MatrixInstance,
  HighlightState,
} from "@/types/types";
import * as d3 from "d3";

export class MultipleMatrixManager {
  private matrices: Map<string, MatrixInstance> = new Map();
  private eventBus: MatrixEventBus;
  private columns: string[]; // Supports arbitrary number of columns
  private csvData: Row[];
  private invalidIndices: number[] = [];

  constructor(
    eventBus: MatrixEventBus,
    columns: string[], // No longer limited to three columns
    csvData: Row[]
  ) {
    // Validate column count
    if (columns.length < 3) {
      throw new Error(
        `MultipleMatrixManager requires at least 3 columns, got ${columns.length}`
      );
    }

    this.eventBus = eventBus;
    this.columns = columns;
    this.csvData = csvData;
    this.setupEventListeners();

    console.log(
      `MultipleMatrixManager initialized with ${
        columns.length
      } columns: [${columns.join(", ")}]`
    );
  }

  private setupEventListeners(): void {
    // Listen for matrix cell click events
    this.eventBus.on("matrix-cell-clicked", (event: any) => {
      this.handleMatrixCellClick(event);
    });

    // Listen for conflict area click events
    this.eventBus.on("conflict-area-clicked", (event: any) => {
      this.handleConflictAreaClick(event);
    });

    // Listen for condition area click events
    this.eventBus.on("condition-area-clicked", (event: any) => {
      this.handleConditionAreaClick(event);
    });

    // Listen for bar click events (handled only in multi-matrix environment)
    this.barClickHandler = (event: Event) => {
      this.handleBarClick(event as CustomEvent);
    };
    window.addEventListener("matrix-bar-clicked", this.barClickHandler);

    // Listen for global clear highlight events
    this.clearHighlightHandler = (event: Event) => {
      this.handleClearAllHighlights(event as CustomEvent);
    };
    window.addEventListener(
      "clear-all-matrix-highlights",
      this.clearHighlightHandler
    );
  }

  // Store event handler references for cleanup
  private barClickHandler?: (event: Event) => void;
  private clearHighlightHandler?: (event: Event) => void;

  /**
   * Handle global clear highlight events
   */
  private handleClearAllHighlights(event: CustomEvent): void {
    // Clear highlights and labels for all matrices
    this.clearAllHighlights();

    // Trigger external event to notify other components
    const clearEvent = new CustomEvent("highlight-invalid-data", {
      detail: {
        rowIds: [],
        highlightColumns: [],
        sortedIndices: [],
        isRightClick: false,
        isFromBarClick: true, // Mark as event from bar click
        isClearEvent: true, // Mark as clear event
      },
    });
    window.dispatchEvent(clearEvent);
  }

  /**
   * Handle bar click events for intelligent highlighting
   */
  private handleBarClick(event: CustomEvent): void {
    const { category, column, columnIndex, chartPosition, matrixColumns } =
      event.detail;

    // Clear all existing highlights
    this.clearAllHighlights();

    // Analyze the relationship between the clicked bar and validation rules
    const barAnalysis = this.analyzeBarValidation(category, column);

    // Apply intelligent highlighting based on analysis
    this.applyIntelligentHighlighting(category, column, barAnalysis);

    // Trigger external event, marking it as a bar click
    const highlightEvent = new CustomEvent("highlight-invalid-data", {
      detail: {
        rowIds: [],
        highlightColumns: [column],
        sortedIndices: [],
        isRightClick: false,
        isFromBarClick: true,
        clickedCategory: category,
        clickedColumn: column,
      },
    });
    window.dispatchEvent(highlightEvent);
  }

  /**
   * Analyze the relationship between the bar and validation rules.
   * Correctly analyzes the clicked bar and related bar types.
   */
  private analyzeBarValidation(
    category: string,
    column: string
  ): {
    clickedBarType: "valid" | "invalid" | "conflict";
    relatedCategories: Map<
      string,
      {
        type: "valid" | "invalid" | "conflict";
        categories: Map<string, "valid" | "invalid" | "conflict">;
      }
    >;
  } {
    const result = {
      clickedBarType: "valid" as "valid" | "invalid" | "conflict",
      relatedCategories: new Map<
        string,
        {
          type: "valid" | "invalid" | "conflict";
          categories: Map<string, "valid" | "invalid" | "conflict">;
        }
      >(),
    };

    // Initialize results for other columns
    this.columns.forEach((col) => {
      if (col !== column) {
        result.relatedCategories.set(col, {
          type: "valid",
          categories: new Map<string, "valid" | "invalid" | "conflict">(),
        });
      }
    });

    // Get index of current column in global configuration
    const columnIndex = this.columns.indexOf(column);
    if (columnIndex === -1) {
      return result;
    }

    // Analyze the clicked bar itself: Count all data containing this category
    let clickedBarHasValid = false;
    let clickedBarHasInvalid = false;

    // Analyze all data combinations related to the clicked category
    const relatedCombinations = new Map<
      string,
      { valid: boolean; invalid: boolean }
    >();

    this.csvData.forEach((row, index) => {
      const rowCategoryValue = String(row[column] || "").toLowerCase();

      if (rowCategoryValue === category.toLowerCase()) {
        const isInvalid = this.invalidIndices.includes(index);

        // Count data types for the clicked bar
        if (isInvalid) {
          clickedBarHasInvalid = true;
        } else {
          clickedBarHasValid = true;
        }

        // Create combination keys for every other column and count
        this.columns.forEach((col, colIndex) => {
          if (colIndex !== columnIndex) {
            const otherValue = String(row[col] || "").toLowerCase();
            const combinationKey = `${col}:${otherValue}`;

            if (!relatedCombinations.has(combinationKey)) {
              relatedCombinations.set(combinationKey, {
                valid: false,
                invalid: false,
              });
            }

            const combination = relatedCombinations.get(combinationKey)!;
            if (isInvalid) {
              combination.invalid = true;
            } else {
              combination.valid = true;
            }
          }
        });
      }
    });

    // Determine the type of the clicked bar
    if (clickedBarHasValid && clickedBarHasInvalid) {
      result.clickedBarType = "conflict";
    } else if (clickedBarHasInvalid) {
      result.clickedBarType = "invalid";
    } else {
      result.clickedBarType = "valid";
    }

    // Analyze types for each category in related columns
    relatedCombinations.forEach((combination, combinationKey) => {
      const [colName, categoryValue] = combinationKey.split(":");

      const colData = result.relatedCategories.get(colName);
      if (colData) {
        // Determine the combination type for this category and the clicked category
        let categoryType: "valid" | "invalid" | "conflict";

        if (combination.valid && combination.invalid) {
          categoryType = "conflict";
        } else if (combination.invalid) {
          categoryType = "invalid";
        } else {
          categoryType = "valid";
        }

        colData.categories.set(categoryValue, categoryType);
      }
    });

    return result;
  }

  /**
   * Apply intelligent highlighting using the analysis structure.
   */
  private applyIntelligentHighlighting(
    clickedCategory: string,
    clickedColumn: string,
    analysis: {
      clickedBarType: "valid" | "invalid" | "conflict";
      relatedCategories: Map<
        string,
        {
          type: "valid" | "invalid" | "conflict";
          categories: Map<string, "valid" | "invalid" | "conflict">;
        }
      >;
    }
  ): void {
    // Iterate through all matrices
    this.matrices.forEach((matrix, matrixId) => {
      const config = matrix.config;
      const [col1, col2] = config.columns;

      const highlightState: HighlightState = {
        matrixId,
        category1Highlights: [],
        category2Highlights: [],
        cellHighlights: [],
      };

      // Handle highlighting for the first column
      if (col1 === clickedColumn) {
        // Clicked column is the first column of the current matrix
        const color = this.getBarTypeColor(analysis.clickedBarType);
        highlightState.category1Highlights.push({
          category: clickedCategory,
          color: color,
          edges: this.getVisibleEdgesForMatrix(
            matrixId,
            "category1",
            config.edges
          ),
        });
      } else if (analysis.relatedCategories.has(col1)) {
        // First column of the current matrix is a related column
        const relatedInfo = analysis.relatedCategories.get(col1)!;

        // Add highlight for each related category using its specific color
        relatedInfo.categories.forEach((categoryType, categoryValue) => {
          const color = this.getBarTypeColor(categoryType);
          highlightState.category1Highlights.push({
            category: categoryValue,
            color: color,
            edges: this.getVisibleEdgesForMatrix(
              matrixId,
              "category1",
              config.edges
            ),
          });
        });
      }

      // Handle highlighting for the second column
      if (col2 === clickedColumn) {
        // Clicked column is the second column of the current matrix
        const color = this.getBarTypeColor(analysis.clickedBarType);
        highlightState.category2Highlights.push({
          category: clickedCategory,
          color: color,
          edges: this.getVisibleEdgesForMatrix(
            matrixId,
            "category2",
            config.edges
          ),
        });
      } else if (analysis.relatedCategories.has(col2)) {
        // Second column of the current matrix is a related column
        const relatedInfo = analysis.relatedCategories.get(col2)!;

        // Add highlight for each related category using its specific color
        relatedInfo.categories.forEach((categoryType, categoryValue) => {
          const color = this.getBarTypeColor(categoryType);
          highlightState.category2Highlights.push({
            category: categoryValue,
            color: color,
            edges: this.getVisibleEdgesForMatrix(
              matrixId,
              "category2",
              config.edges
            ),
          });
        });
      }

      // Apply highlights
      if (
        highlightState.category1Highlights.length > 0 ||
        highlightState.category2Highlights.length > 0
      ) {
        this.updateMatrixHighlights(matrixId, highlightState);
      }
    });
  }

  /**
   * Get color based on bar type
   */
  private getBarTypeColor(barType: "valid" | "invalid" | "conflict"): string {
    switch (barType) {
      case "valid":
        return "#4570b6"; // Dark Blue
      case "invalid":
        return "#fdae6b"; // Orange
      case "conflict":
        return "#FBDE71"; // Yellow (previously gray)
      default:
        return "#4570b6";
    }
  }

  /**
   * Clean up listeners
   */
  public destroy(): void {
    if (this.barClickHandler) {
      window.removeEventListener("matrix-bar-clicked", this.barClickHandler);
    }
    if (this.clearHighlightHandler) {
      window.removeEventListener(
        "clear-all-matrix-highlights",
        this.clearHighlightHandler
      );
    }
  }

  /**
   * Handle matrix cell click, implementing cross-matrix interaction
   */
  private handleMatrixCellClick(event: any): void {
    const {
      matrixId,
      category1,
      category2,
      cellType,
      isRightClick,
      rowIds,
      sortedIndices,
    } = event;

    // Analyze related data and find cross-matrix relations
    const crossMatrixData = this.analyzeCrossMatrixRelations(
      matrixId,
      category1,
      category2,
      rowIds
    );

    // Clear all matrix highlights
    this.clearAllHighlights();

    // Highlight source matrix using correct color logic
    this.highlightSourceMatrix(matrixId, category1, category2, cellType);

    // Highlight related matrices passing detailed data analysis and source cell type
    this.highlightRelatedMatrices(
      matrixId,
      crossMatrixData,
      cellType,
      category1,
      category2
    );

    // Trigger external events
    this.emitExternalEvents(event, crossMatrixData);
  }

  /**
   * Analyze cross-matrix related data - Supports dynamic column counts and matrix quantities
   */
  private analyzeCrossMatrixRelations(
    sourceMatrixId: string,
    category1: string,
    category2: string,
    rowIds: number[]
  ): Map<
    string,
    {
      validCategories: string[];
      invalidCategories: string[];
      conflictCategories: string[];
      rowIds: number[];
    }
  > {
    const crossMatrixData = new Map<
      string,
      {
        validCategories: string[];
        invalidCategories: string[];
        conflictCategories: string[];
        rowIds: number[];
      }
    >();

    // Get source matrix configuration
    const sourceMatrix = this.matrices.get(sourceMatrixId);
    if (!sourceMatrix) {
      return crossMatrixData;
    }

    const sourceConfig = sourceMatrix.config;
    const [sourceCol1, sourceCol2] = sourceConfig.columns;

    // Find all data rows in source matrix matching the clicked categories
    const matchingRows: number[] = [];
    this.csvData.forEach((row, index) => {
      const sourceVal1 = String(row[sourceCol1] || "").toLowerCase();
      const sourceVal2 = String(row[sourceCol2] || "").toLowerCase();

      if (
        sourceVal1 === category1.toLowerCase() &&
        sourceVal2 === category2.toLowerCase()
      ) {
        matchingRows.push(index);
      }
    });

    // Analyze related data for every other matrix
    this.matrices.forEach((targetMatrix, targetMatrixId) => {
      // Skip the source matrix itself
      if (targetMatrixId === sourceMatrixId) return;

      const targetConfig = targetMatrix.config;
      const [targetCol1, targetCol2] = targetConfig.columns;

      const validCategoriesCol1 = new Set<string>();
      const invalidCategoriesCol1 = new Set<string>();
      const conflictCategoriesCol1 = new Set<string>();

      const validCategoriesCol2 = new Set<string>();
      const invalidCategoriesCol2 = new Set<string>();
      const conflictCategoriesCol2 = new Set<string>();

      const relatedRowIds: number[] = [];

      // Analyze matching rows
      matchingRows.forEach((index) => {
        relatedRowIds.push(index);
        const isInvalid = this.invalidIndices.includes(index);

        const row = this.csvData[index];
        const targetVal1 = String(row[targetCol1] || "").toLowerCase();
        const targetVal2 = String(row[targetCol2] || "").toLowerCase();

        // Add categories for the first column
        if (isInvalid) {
          invalidCategoriesCol1.add(targetVal1);
        } else {
          validCategoriesCol1.add(targetVal1);
        }

        // Add categories for the second column
        if (isInvalid) {
          invalidCategoriesCol2.add(targetVal2);
        } else {
          validCategoriesCol2.add(targetVal2);
        }
      });

      // Check for conflicts (same category has both valid and invalid entries)
      validCategoriesCol1.forEach((category) => {
        if (invalidCategoriesCol1.has(category)) {
          conflictCategoriesCol1.add(category);
          validCategoriesCol1.delete(category);
          invalidCategoriesCol1.delete(category);
        }
      });

      validCategoriesCol2.forEach((category) => {
        if (invalidCategoriesCol2.has(category)) {
          conflictCategoriesCol2.add(category);
          validCategoriesCol2.delete(category);
          invalidCategoriesCol2.delete(category);
        }
      });

      // Merge all categories
      const allValidCategories = [
        ...Array.from(validCategoriesCol1),
        ...Array.from(validCategoriesCol2),
      ];

      const allInvalidCategories = [
        ...Array.from(invalidCategoriesCol1),
        ...Array.from(invalidCategoriesCol2),
      ];

      const allConflictCategories = [
        ...Array.from(conflictCategoriesCol1),
        ...Array.from(conflictCategoriesCol2),
      ];

      if (
        allValidCategories.length > 0 ||
        allInvalidCategories.length > 0 ||
        allConflictCategories.length > 0
      ) {
        const result = {
          validCategories: allValidCategories,
          invalidCategories: allInvalidCategories,
          conflictCategories: allConflictCategories,
          rowIds: relatedRowIds,
        };

        crossMatrixData.set(targetMatrixId, result);
      }
    });

    return crossMatrixData;
  }

  /**
   * Highlight source matrix using the correct color
   */
  private highlightSourceMatrix(
    matrixId: string,
    category1: string,
    category2: string,
    cellType: string
  ): void {
    const matrix = this.matrices.get(matrixId);
    if (!matrix) return;

    const config = matrix.config;

    // Determine highlight color based on cellType
    let sourceColor: string;
    if (cellType === "conflict") {
      // Conflict area: Analyze specific data types to determine highlight color
      const conflictHighlights = this.analyzeConflictHighlights(
        matrixId,
        category1,
        category2
      );

      // Create special highlight state for conflict area
      const highlightState: HighlightState = {
        matrixId,
        category1Highlights: conflictHighlights.category1Highlights,
        category2Highlights: conflictHighlights.category2Highlights,
        cellHighlights: [
          {
            category1,
            category2,
            color: "#a8a8a8", // Use gray for the conflict area itself
          },
        ],
      };

      this.updateMatrixHighlights(matrixId, highlightState);
      return;
    } else {
      sourceColor = this.getCellTypeColor(cellType);
    }

    const highlightState: HighlightState = {
      matrixId,
      category1Highlights: [
        {
          category: category1,
          color: sourceColor,
          edges: this.getVisibleEdgesForMatrix(
            matrixId,
            "category1",
            config.edges
          ),
        },
      ],
      category2Highlights: [
        {
          category: category2,
          color: sourceColor,
          edges: this.getVisibleEdgesForMatrix(
            matrixId,
            "category2",
            config.edges
          ),
        },
      ],
      cellHighlights: [
        {
          category1,
          category2,
          color: sourceColor,
        },
      ],
    };

    this.updateMatrixHighlights(matrixId, highlightState);
  }

  /**
   * Analyze highlight colors for conflict areas
   */
  private analyzeConflictHighlights(
    matrixId: string,
    category1: string,
    category2: string
  ): {
    category1Highlights: { category: string; color: string; edges: string[] }[];
    category2Highlights: { category: string; color: string; edges: string[] }[];
  } {
    const matrix = this.matrices.get(matrixId);
    if (!matrix) {
      return { category1Highlights: [], category2Highlights: [] };
    }

    const config = matrix.config;
    const category1Highlights: {
      category: string;
      color: string;
      edges: string[];
    }[] = [];
    const category2Highlights: {
      category: string;
      color: string;
      edges: string[];
    }[] = [];

    // Add highlight for category1 (Yellow)
    category1Highlights.push({
      category: category1,
      color: "#FBDE71",
      edges: this.getVisibleEdgesForMatrix(matrixId, "category1", config.edges),
    });

    // Add highlight for category2 (Yellow)
    category2Highlights.push({
      category: category2,
      color: "#FBDE71",
      edges: this.getVisibleEdgesForMatrix(matrixId, "category2", config.edges),
    });

    return { category1Highlights, category2Highlights };
  }

  /**
   * Highlight related matrices - Handle shared edge label display intelligently
   */
  private highlightRelatedMatrices(
    sourceMatrixId: string,
    crossMatrixData: Map<
      string,
      {
        validCategories: string[];
        invalidCategories: string[];
        conflictCategories: string[];
        rowIds: number[];
      }
    >,
    sourceCellType: string,
    sourceCategory1: string,
    sourceCategory2: string
  ): void {
    crossMatrixData.forEach((data, targetMatrixId) => {
      // Skip source matrix
      if (targetMatrixId === sourceMatrixId) return;

      const matrix = this.matrices.get(targetMatrixId);
      if (!matrix) {
        return;
      }

      const config = matrix.config;
      const [targetCol1, targetCol2] = config.columns;

      // Create highlight state, using different colors based on data type
      const highlightState: HighlightState = {
        matrixId: targetMatrixId,
        category1Highlights: [],
        category2Highlights: [],
        cellHighlights: [],
      };

      // Get source color
      const sourceColor = this.getCellTypeColor(sourceCellType);

      // Process related categories found across matrices
      const processCategories = (categories: string[], color: string) => {
        categories.forEach((category) => {
          // Check if category matches the first or second column in the target matrix
          let categoryType = "category1";
          let edges: string[] = [];

          if (targetCol1 === category) {
            categoryType = "category1";
            edges = this.getVisibleEdgesForMatrix(
              targetMatrixId,
              categoryType,
              config.edges
            );
            highlightState.category1Highlights.push({
              category,
              color,
              edges,
            });
          } else if (targetCol2 === category) {
            categoryType = "category2";
            edges = this.getVisibleEdgesForMatrix(
              targetMatrixId,
              categoryType,
              config.edges
            );
            highlightState.category2Highlights.push({
              category,
              color,
              edges,
            });
          } else {
            // If category is not the column name itself but a value in the column, perform complex matching
            let found = false;

            // Check first column
            const col1Values = new Set(
              this.csvData.map((row) =>
                String(row[targetCol1] || "").toLowerCase()
              )
            );
            if (col1Values.has(category.toLowerCase())) {
              categoryType = "category1";
              edges = this.getVisibleEdgesForMatrix(
                targetMatrixId,
                categoryType,
                config.edges
              );
              highlightState.category1Highlights.push({
                category,
                color,
                edges,
              });
              found = true;
            }

            // Check second column
            const col2Values = new Set(
              this.csvData.map((row) =>
                String(row[targetCol2] || "").toLowerCase()
              )
            );
            if (col2Values.has(category.toLowerCase())) {
              categoryType = "category2";
              edges = this.getVisibleEdgesForMatrix(
                targetMatrixId,
                categoryType,
                config.edges
              );
              highlightState.category2Highlights.push({
                category,
                color,
                edges,
              });
              found = true;
            }
          }
        });
      };

      if (sourceCellType === "conflict") {
        // Conflict area: Highlight based on actual data types
        processCategories(data.validCategories, "#4570b6"); // Blue
        processCategories(data.invalidCategories, "#fdae6b"); // Orange
        processCategories(data.conflictCategories, "#FBDE71"); // Yellow
      } else {
        // Non-conflict area: Use source color for all related categories
        const allRelatedCategories = [
          ...data.validCategories,
          ...data.invalidCategories,
          ...data.conflictCategories,
        ];

        processCategories(allRelatedCategories, sourceColor);
      }

      // Apply highlights
      this.updateMatrixHighlights(targetMatrixId, highlightState);
    });
  }

  /**
   * Get visible edges configuration for a matrix.
   * Only returns edges required by the configuration.
   */
  private getVisibleEdgesForMatrix(
    matrixId: string,
    categoryType: string,
    configuredEdges: string[]
  ): string[] {
    let possibleEdges: string[] = [];

    if (categoryType === "category1") {
      // Horizontal edges
      possibleEdges = ["bottom", "top"];
    } else {
      // Vertical edges
      possibleEdges = ["right", "left"];
    }

    // Filter to return only edges present in configuration
    const visibleEdges = possibleEdges.filter((edge) =>
      configuredEdges.includes(edge)
    );

    return visibleEdges;
  }

  /**
   * Get color based on cell type
   */
  private getCellTypeColor(cellType: string): string {
    switch (cellType) {
      case "valid":
        return "#4570b6"; // Dark Blue
      case "conflict":
        return "#FBDE71"; // Yellow
      case "invalid":
      default:
        return "#fd8d3c"; // Orange
    }
  }

  /**
   * Trigger external events.
   * Passes different data to the table based on area type.
   */
  private emitExternalEvents(
    originalEvent: any,
    crossMatrixData: Map<
      string,
      {
        validCategories: string[];
        invalidCategories: string[];
        conflictCategories: string[];
        rowIds: number[];
      }
    >
  ): void {
    // Collect all related row IDs (for cross-matrix interaction)
    const allRowIds = new Set<number>(originalEvent.rowIds || []);
    crossMatrixData.forEach((data) => {
      data.rowIds.forEach((id) => allRowIds.add(id));
    });

    // Determine data to pass to table based on cellType
    let tableRowIds: number[];

    if (originalEvent.cellType === "valid") {
      // Clicked valid area: Show all global invalid data
      tableRowIds = this.invalidIndices.slice();
    } else if (
      originalEvent.cellType === "invalid" ||
      originalEvent.cellType === "conflict"
    ) {
      // Clicked invalid or conflict area: Show only invalid data related to this area
      tableRowIds = Array.from(allRowIds).filter((rowId) =>
        this.invalidIndices.includes(rowId)
      );
    } else {
      // Default: Show related invalid data
      tableRowIds = Array.from(allRowIds).filter((rowId) =>
        this.invalidIndices.includes(rowId)
      );
    }

    // Trigger highlight event for the table
    const highlightEvent = new CustomEvent("highlight-invalid-data", {
      detail: {
        rowIds: tableRowIds,
        highlightColumns: this.columns,
        sortedIndices: tableRowIds,
        isRightClick: originalEvent.isRightClick || false,
        isFromMatrixClick: true,
        cellType: originalEvent.cellType,
        originalRowIds: Array.from(allRowIds), // Keep original data for debugging
      },
    });
    window.dispatchEvent(highlightEvent);
  }

  /**
   * Handle conflict area click
   */
  private handleConflictAreaClick(event: any): void {
    // Implement cross-matrix interaction logic for conflict areas
    this.handleMatrixCellClick({
      ...event,
      cellType: "conflict",
    });
  }

  /**
   * Handle condition area click
   */
  private handleConditionAreaClick(event: any): void {
    // Implement cross-matrix interaction logic for condition areas
    this.handleMatrixCellClick({
      ...event,
      cellType: "valid",
    });
  }

  /**
   * Register a matrix instance
   */
  public registerMatrix(id: string, matrix: MatrixInstance): void {
    this.matrices.set(id, matrix);
    console.log(`Matrix ${id} registered`);
  }

  /**
   * Set invalid data indices
   */
  public setInvalidIndices(indices: number[]): void {
    this.invalidIndices = indices;
  }

  /**
   * Get statistics
   */
  public getStats(): any {
    return {
      matricesCount: this.matrices.size,
      registeredMatrices: Array.from(this.matrices.keys()),
      invalidIndicesCount: this.invalidIndices.length,
    };
  }

  /**
   * Get all registered matrix IDs
   */
  public getRegisteredMatrices(): string[] {
    return Array.from(this.matrices.keys());
  }

  /**
   * Update matrix highlight state, including label display.
   * Correctly handles cross-matrix label display.
   */
  public updateMatrixHighlights(
    matrixId: string,
    highlightState: HighlightState
  ): void {
    const matrix = this.matrices.get(matrixId);
    if (!matrix) {
      return;
    }

    // Update matrix highlights (handles bar highlighting)
    matrix.updateHighlights(highlightState);

    // Show related labels using enhanced logic
    this.showMatrixLabelsEnhanced(matrixId, highlightState);
  }

  /**
   * Enhanced label display method.
   * Only shows labels for visible edges.
   */
  private showMatrixLabelsEnhanced(
    matrixId: string,
    highlightState: HighlightState
  ): void {
    const matrix = this.matrices.get(matrixId);
    if (!matrix) return;

    const svg = matrix.svg;
    const config = matrix.config;

    // Show category1 labels (horizontal edges) - Only for visible edges
    highlightState.category1Highlights.forEach((highlight) => {
      highlight.edges.forEach((edge) => {
        // Ensure this edge is visible in configuration
        if (config.edges.includes(edge)) {
          const labels = svg.selectAll(
            `.edge-label[data-edge="${edge}"][data-category="${highlight.category.toLowerCase()}"]`
          );
          labels.style("visibility", "visible");
        }
      });
    });

    // Show category2 labels (vertical edges) - Only for visible edges
    highlightState.category2Highlights.forEach((highlight) => {
      highlight.edges.forEach((edge) => {
        // Ensure this edge is visible in configuration
        if (config.edges.includes(edge)) {
          const labels = svg.selectAll(
            `.edge-label[data-edge="${edge}"][data-category="${highlight.category.toLowerCase()}"]`
          );
          labels.style("visibility", "visible");
        }
      });
    });
  }

  /**
   * Hide all labels for a specific matrix
   */
  private hideMatrixLabels(matrixId: string): void {
    const matrix = this.matrices.get(matrixId);
    if (!matrix) return;

    matrix.svg.selectAll(".edge-label").style("visibility", "hidden");
  }

  /**
   * Hide labels for all matrices
   */
  public hideAllLabels(): void {
    this.matrices.forEach((matrix, matrixId) => {
      this.hideMatrixLabels(matrixId);
    });
  }

  /**
   * Clear highlights for all matrices
   */
  public clearAllHighlights(): void {
    this.matrices.forEach((matrix) => {
      if (matrix.clearHighlights) {
        matrix.clearHighlights();
      }
    });
    this.hideAllLabels();
  }
}

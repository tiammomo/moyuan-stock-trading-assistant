"use client";

import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type { ResultTable as ResultTableType, JsonValue } from "@/types/common";

const columnHelper = createColumnHelper<Record<string, JsonValue>>();

interface ResultTableProps {
  table: ResultTableType | null;
  onRowClick?: (row: Record<string, JsonValue>) => void;
  onFavorite?: (row: Record<string, JsonValue>) => void;
}

export function ResultTable({ table, onRowClick, onFavorite }: ResultTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [favoritedRows, setFavoritedRows] = useState<Set<number>>(new Set());

  if (!table || table.rows.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        暂无表格数据
      </div>
    );
  }

  const columns = table.columns.map((col) =>
    columnHelper.accessor(col, {
      header: col,
      cell: (info) => {
        const value = info.getValue();
        const formatted = String(value ?? "-");
        const isNumeric = typeof value === "number";
        return (
          <span
            className={cn(
              "truncate block",
              isNumeric && "font-mono text-right",
              formatted.startsWith("-") && "text-red-500",
              formatted.startsWith("+") && "text-green-600"
            )}
          >
            {formatted}
          </span>
        );
      },
    })
  );

  const tableInstance = useReactTable({
    data: table.rows,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const handleFavorite = (rowIndex: number, row: Record<string, JsonValue>) => {
    const newSet = new Set(favoritedRows);
    if (newSet.has(rowIndex)) {
      newSet.delete(rowIndex);
    } else {
      newSet.add(rowIndex);
      onFavorite?.(row);
    }
    setFavoritedRows(newSet);
  };

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Input
          placeholder="🔍 搜索..."
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          className="h-8 text-xs pl-8"
        />
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50 text-xs">
          🔍
        </span>
      </div>

      {/* Table */}
      <div className="border rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-auto max-h-[400px]">
          <table className="w-full text-sm">
            <thead className="bg-gradient-to-r from-muted/80 to-muted/50 sticky top-0 z-10">
              {tableInstance.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground cursor-pointer hover:bg-muted/80 transition-colors select-none"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center gap-1.5">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() && (
                          <span className="text-primary">
                            {header.column.getIsSorted() === "asc" ? "↑" : "↓"}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                  <th className="px-3 py-2.5 w-12"></th>
                </tr>
              ))}
            </thead>
            <tbody>
              {tableInstance.getRowModel().rows.map((row, rowIndex) => {
                const isFavorited = favoritedRows.has(rowIndex);
                const isEven = rowIndex % 2 === 0;

                return (
                  <tr
                    key={row.id}
                    className={cn(
                      "border-t border-border/30 transition-all duration-150",
                      isEven ? "bg-transparent" : "bg-muted/20",
                      "hover:bg-primary/5 hover:shadow-sm cursor-pointer group"
                    )}
                    onClick={() => onRowClick?.(row.original)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2.5 text-sm">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                    <td className="px-3 py-2.5">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleFavorite(rowIndex, row.original);
                        }}
                        className={cn(
                          "w-7 h-7 rounded-lg flex items-center justify-center text-sm transition-all duration-200",
                          isFavorited
                            ? "text-yellow-500 bg-yellow-50 hover:bg-yellow-100"
                            : "text-muted-foreground/30 hover:text-yellow-500 hover:bg-yellow-50 opacity-0 group-hover:opacity-100"
                        )}
                      >
                        {isFavorited ? "★" : "☆"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          共 {table.rows.length} 条结果
          {globalFilter && ` · 筛选后`
          }
        </span>
        <span className="flex items-center gap-1">
          <span className="text-yellow-500">☆</span> 点击收藏可加入候选池
        </span>
      </div>
    </div>
  );
}

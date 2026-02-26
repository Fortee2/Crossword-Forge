from typing import List, Dict, Any
from collections import deque


def validate_grid(grid_data: List[List[Dict[str, Any]]], symmetry_enabled: bool = True) -> Dict[str, Any]:
    """
    Validate a crossword grid and return warnings.

    Grid cell format: {"isBlack": bool, "letter": str}
    """
    warnings = []
    size = len(grid_data)

    if size != 15 or any(len(row) != 15 for row in grid_data):
        warnings.append({
            "type": "invalid_size",
            "message": "Grid must be 15x15"
        })
        return {"valid": False, "warnings": warnings}

    # Check for isolated regions
    isolated_regions = find_isolated_regions(grid_data)
    if isolated_regions:
        warnings.append({
            "type": "isolated_regions",
            "message": f"Grid has {len(isolated_regions)} isolated white region(s)",
            "cells": isolated_regions
        })

    # Check for words shorter than 3 letters
    short_words = find_short_words(grid_data)
    if short_words:
        warnings.append({
            "type": "short_words",
            "message": f"Found {len(short_words)} word(s) shorter than 3 letters",
            "words": short_words
        })

    # Check symmetry if enabled
    if symmetry_enabled:
        broken_symmetry = check_symmetry(grid_data)
        if broken_symmetry:
            warnings.append({
                "type": "broken_symmetry",
                "message": f"Found {len(broken_symmetry)} cell(s) breaking rotational symmetry",
                "cells": broken_symmetry
            })

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings
    }


def find_isolated_regions(grid_data: List[List[Dict[str, Any]]]) -> List[List[Dict[str, int]]]:
    """Find isolated white cell regions using flood fill."""
    size = len(grid_data)
    visited = [[False] * size for _ in range(size)]
    regions = []

    def flood_fill(start_row: int, start_col: int) -> List[Dict[str, int]]:
        region = []
        queue = deque([(start_row, start_col)])
        visited[start_row][start_col] = True

        while queue:
            row, col = queue.popleft()
            region.append({"row": row, "col": col})

            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < size and 0 <= nc < size and not visited[nr][nc]:
                    if not grid_data[nr][nc].get("isBlack", False):
                        visited[nr][nc] = True
                        queue.append((nr, nc))

        return region

    for row in range(size):
        for col in range(size):
            if not visited[row][col] and not grid_data[row][col].get("isBlack", False):
                region = flood_fill(row, col)
                regions.append(region)

    # If there's more than one region, all but the largest are "isolated"
    if len(regions) > 1:
        regions.sort(key=len, reverse=True)
        return regions[1:]  # Return all except the largest

    return []


def find_short_words(grid_data: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Find words (consecutive white squares) shorter than 3 letters."""
    size = len(grid_data)
    short_words = []

    # Check horizontal words
    for row in range(size):
        col = 0
        while col < size:
            if not grid_data[row][col].get("isBlack", False):
                start_col = col
                while col < size and not grid_data[row][col].get("isBlack", False):
                    col += 1
                length = col - start_col
                if 1 < length < 3:
                    short_words.append({
                        "direction": "across",
                        "row": row,
                        "col": start_col,
                        "length": length
                    })
            else:
                col += 1

    # Check vertical words
    for col in range(size):
        row = 0
        while row < size:
            if not grid_data[row][col].get("isBlack", False):
                start_row = row
                while row < size and not grid_data[row][col].get("isBlack", False):
                    row += 1
                length = row - start_row
                if 1 < length < 3:
                    short_words.append({
                        "direction": "down",
                        "row": start_row,
                        "col": col,
                        "length": length
                    })
            else:
                row += 1

    return short_words


def check_symmetry(grid_data: List[List[Dict[str, Any]]]) -> List[Dict[str, int]]:
    """Check for 180-degree rotational symmetry violations."""
    size = len(grid_data)
    broken = []

    for row in range(size):
        for col in range(size):
            mirror_row = size - 1 - row
            mirror_col = size - 1 - col

            is_black = grid_data[row][col].get("isBlack", False)
            mirror_is_black = grid_data[mirror_row][mirror_col].get("isBlack", False)

            if is_black != mirror_is_black:
                # Only add each pair once
                if row < mirror_row or (row == mirror_row and col < mirror_col):
                    broken.append({"row": row, "col": col})

    return broken

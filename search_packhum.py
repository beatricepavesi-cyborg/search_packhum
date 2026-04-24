#!/usr/bin/env python3
"""
search_packhum.py - Search iphi.json with multiple filters and export results to CSV

Usage:
    python search_packhum.py --text "θεοπομπου"
    python search_packhum.py --region_main "Central Greece" --region_sub "Boiotia"
    python search_packhum.py --region_main_id "1698" --region_sub_id "1691"
    python search_packhum.py --date_min "-275" --date_max "-226"
    python search_packhum.py --date_circa True
    python search_packhum.py --id 27869 --text "θεοπομπου"

For more help: python search_packhum.py --help
"""

import json
import csv
import argparse
import sys
from pathlib import Path

def load_data(json_path='iphi.json'):
    """Load the JSON data from file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"Warning: Expected list, got {type(data).__name__}")
            return [data] if data else []
        return data
    except FileNotFoundError:
        print(f"Error: {json_path} not found in current directory")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}")
        sys.exit(1)

def search_entries(entries, filters, case_sensitive=False):
    """
    Search entries based on provided filters
    Filters is a dict of field -> search value
    Handles special cases: region_main_id takes precedence over region_main
    """
    results = []
    
    # Handle region priority: if region_main_id is present, ignore region_main
    if 'region_main_id' in filters and filters['region_main_id'] is not None:
        filters.pop('region_main', None)
    
    # Handle region_sub priority: if region_sub_id is present, ignore region_sub
    if 'region_sub_id' in filters and filters['region_sub_id'] is not None:
        filters.pop('region_sub', None)
    
    for entry in entries:
        match = True
        for field, search_value in filters.items():
            if search_value is None:
                continue
                
            # Get the field value from entry, default to empty string if not present
            field_value = entry.get(field, '')
            
            # Special handling for date_circa (boolean)
            if field == 'date_circa':
                field_value_bool = field_value if field_value is not None else False
                search_value_bool = str(search_value).lower() in ['true', '1', 'yes', 't']
                if field_value_bool != search_value_bool:
                    match = False
                    break
                continue
            
            # For ID, use exact match
            if field == 'id':
                try:
                    if int(field_value) != int(search_value):
                        match = False
                        break
                except (ValueError, TypeError):
                    match = False
                    break
                continue
            
            # For other fields, use substring match
            # Convert to string for comparison
            field_value_str = str(field_value) if field_value is not None else ''
            search_value_str = str(search_value)
            
            if case_sensitive:
                if search_value_str not in field_value_str:
                    match = False
                    break
            else:
                if search_value_str.lower() not in field_value_str.lower():
                    match = False
                    break
                
        if match:
            results.append(entry)
    
    return results

def write_to_csv(results, output_file):
    """Write search results to CSV file"""
    if not results:
        print("No results to write")
        return False
    
    # Get all possible field names from all results
    fieldnames = set()
    for entry in results:
        fieldnames.update(entry.keys())
    
    # Sort fieldnames for consistent output
    fieldnames = sorted(fieldnames)
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        return True
    except Exception as e:
        print(f"Error writing CSV: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Search iphi.json (Packhum Greek inscriptions) and export results to CSV',
        epilog="""
Examples:
  %(prog)s --text θεοπομπου
  %(prog)s --region_main "Central Greece"
  %(prog)s --region_main_id "1698" --region_sub_id "1691"
  %(prog)s --id 27869
  %(prog)s --date_min "-275" --date_max "-226"
  %(prog)s --date_circa True
  %(prog)s --region_main "Peloponnesos" --date_circa False --max-results 10
  %(prog)s --text "φιλεταιρος" --metadata "Pergameus"

Note: When both region_main and region_main_id are provided, region_main_id takes precedence.
      Similarly, region_sub_id takes precedence over region_sub.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Search filters - Text and metadata
    parser.add_argument('--text', type=str, 
                       help='Search in text field (Greek inscription text)')
    parser.add_argument('--metadata', type=str, 
                       help='Search in metadata field (publication and reference info)')
    
    # Region filters (prefer ID versions for exact matching)
    parser.add_argument('--region_main', type=str, 
                       help='Search in region_main field (main region name)')
    parser.add_argument('--region_main_id', type=str, 
                       help='Search in region_main_id field (precise region ID - takes precedence over region_main)')
    parser.add_argument('--region_sub', type=str, 
                       help='Search in region_sub field (sub-region name)')
    parser.add_argument('--region_sub_id', type=str, 
                       help='Search in region_sub_id field (precise sub-region ID - takes precedence over region_sub)')
    
    # Date filters
    parser.add_argument('--date_str', type=str, 
                       help='Search in date_str field (human-readable date string)')
    parser.add_argument('--date_min', type=str, 
                       help='Search in date_min field (minimum year, e.g., "-275" for 275 BCE)')
    parser.add_argument('--date_max', type=str, 
                       help='Search in date_max field (maximum year, e.g., "-226" for 226 BCE)')
    parser.add_argument('--date_circa', type=str, 
                       choices=['True', 'False', 'true', 'false', '1', '0', 'yes', 'no'],
                       help='Filter by circa dating (True/False)')
    
    # Exact ID filter
    parser.add_argument('--id', type=int, 
                       help='Exact inscription ID number')
    
    # Additional options
    parser.add_argument('--input', type=str, default='iphi.json', 
                       help='Path to JSON file (default: iphi.json)')
    parser.add_argument('--output', type=str, default='results_search_packhum.csv',
                       help='Output CSV filename (default: results_search_packhum.csv)')
    parser.add_argument('--max-results', type=int, default=None,
                       help='Maximum number of results to return (default: all)')
    parser.add_argument('--case-sensitive', action='store_true',
                       help='Enable case-sensitive search (default: case-insensitive)')
    
    args = parser.parse_args()
    
    # Build filters dictionary
    filters = {}
    
    if args.text:
        filters['text'] = args.text
    if args.metadata:
        filters['metadata'] = args.metadata
    if args.region_main:
        filters['region_main'] = args.region_main
    if args.region_main_id:
        filters['region_main_id'] = args.region_main_id
    if args.region_sub:
        filters['region_sub'] = args.region_sub
    if args.region_sub_id:
        filters['region_sub_id'] = args.region_sub_id
    if args.date_str:
        filters['date_str'] = args.date_str
    if args.date_min:
        filters['date_min'] = args.date_min
    if args.date_max:
        filters['date_max'] = args.date_max
    if args.date_circa:
        filters['date_circa'] = args.date_circa
    if args.id is not None:
        filters['id'] = args.id
    
    # Check if at least one filter is provided
    if not filters:
        print("Error: At least one search filter is required")
        print("Use --help to see available filters")
        sys.exit(1)
    
    # Load data
    print(f"Loading data from {args.input}...")
    entries = load_data(args.input)
    print(f"Loaded {len(entries):,} entries")
    
    # Show precedence info if both region versions provided
    if args.region_main and args.region_main_id:
        print("Note: region_main_id takes precedence over region_main")
    if args.region_sub and args.region_sub_id:
        print("Note: region_sub_id takes precedence over region_sub")
    
    # Search
    print(f"Searching with filters: {filters}")
    results = search_entries(entries, filters, args.case_sensitive)
    
    # Apply max results limit
    original_count = len(results)
    if args.max_results and len(results) > args.max_results:
        results = results[:args.max_results]
        print(f"Limited to {args.max_results} results (from {original_count} total matches)")
    else:
        print(f"Found {len(results):,} matching entries")
    
    # Write results to CSV
    if results:
        if write_to_csv(results, args.output):
            print(f"✓ Results written to {args.output}")
            
            # Print first few results as preview
            print(f"\n📋 Preview of first {min(3, len(results))} result(s):")
            for i, result in enumerate(results[:3], 1):
                print(f"\n{'='*60}")
                print(f"Result {i}:")
                print(f"  ID: {result.get('id', 'N/A')}")
                print(f"  Text: {result.get('text', 'N/A')[:150]}..." if len(result.get('text', '')) > 150 else f"  Text: {result.get('text', 'N/A')}")
                print(f"  Region Main: {result.get('region_main', 'N/A')} (ID: {result.get('region_main_id', 'N/A')})")
                print(f"  Region Sub: {result.get('region_sub', 'N/A')} (ID: {result.get('region_sub_id', 'N/A')})")
                print(f"  Date: {result.get('date_str', 'N/A')} (circa: {result.get('date_circa', 'N/A')})")
                if result.get('metadata'):
                    print(f"  Metadata: {result.get('metadata', 'N/A')[:100]}...")
    else:
        print("❌ No matching entries found")
        print("Try broadening your search criteria or check the field values in iphi.json")

if __name__ == "__main__":
    main()
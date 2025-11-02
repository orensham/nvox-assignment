#!/usr/bin/env python3
import csv
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import sys


def validate_csv_rules(rules: List[Dict]) -> List[str]:
    errors = []

    required_fields = ['stage_id', 'if_number_id', 'in_range_min', 'in_range_max', 'next_stage']
    if rules:
        missing = set(required_fields) - set(rules[0].keys())
        if missing:
            errors.append(f"Missing required columns: {missing}")
            return errors

    for i, rule in enumerate(rules, 1):
        row = f"Row {i}"

        for field in required_fields:
            if not rule.get(field):
                errors.append(f"{row}: Empty {field}")

        try:
            min_val = float(rule['in_range_min'])
            max_val = float(rule['in_range_max'])

            if min_val > max_val:
                errors.append(f"{row}: range_min ({min_val}) > range_max ({max_val})")

            if min_val < 0:
                errors.append(f"{row}: Negative range_min ({min_val})")

        except (ValueError, KeyError) as e:
            errors.append(f"{row}: Invalid numeric range - {e}")

    stage_question_ranges = {}
    for i, rule in enumerate(rules, 1):
        key = (rule['stage_id'], rule['if_number_id'])
        if key not in stage_question_ranges:
            stage_question_ranges[key] = []

        try:
            min_val = float(rule['in_range_min'])
            max_val = float(rule['in_range_max'])
            stage_question_ranges[key].append((i, min_val, max_val, rule['next_stage']))
        except (ValueError, KeyError):
            continue

    for (stage, question), ranges in stage_question_ranges.items():
        for i, (row1, min1, max1, dest1) in enumerate(ranges):
            for row2, min2, max2, dest2 in ranges[i + 1:]:

                if not (max1 < min2 or max2 < min1):
                    errors.append(
                        f"Overlapping ranges for {stage}.{question}: "
                        f"Row {row1} [{min1}-{max1}→{dest1}] overlaps "
                        f"Row {row2} [{min2}-{max2}→{dest2}]"
                    )

    return errors


def generate_migration(csv_path: Path, output_dir: Path, migration_num: int = None) -> Path:
    """Generate SQL migration from CSV file."""

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rules = list(reader)

    if not rules:
        print(f"Error: CSV file is empty: {csv_path}")
        sys.exit(1)

    print(f"Read {len(rules)} rules from {csv_path}")

    errors = validate_csv_rules(rules)
    if errors:
        print("\nValidation errors found:\n")
        for error in errors:
            print(f"{error}")
        print("\nFix errors before generating migration")
        sys.exit(1)

    print("Validation passed")

    if migration_num is None:
        existing = sorted(output_dir.glob("*.sql"))
        migration_num = len(existing) + 1

    output_path = output_dir / f"{migration_num:03d}_update_edges_from_csv.sql"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = f"""-- Migration {migration_num:03d}: Update journey edges from CSV
-- Generated: {timestamp}
-- Source: {csv_path.relative_to(Path.cwd())}
-- Total rules: {len(rules)}

BEGIN;

-- Clear existing edges (except entry edge from NULL → REFERRAL)
DELETE FROM journey_edges WHERE from_node_id IS NOT NULL;

-- Re-insert entry edge
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES (NULL, 'REFERRAL', 'always', NULL, NULL, NULL)
ON CONFLICT DO NOTHING;

-- Insert edges from CSV
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
"""

    values = []
    for rule in rules:
        values.append(
            f"    ('{rule['stage_id']}', '{rule['next_stage']}', 'range', "
            f"'{rule['if_number_id']}', {rule['in_range_min']}, {rule['in_range_max']})"
        )

    sql += ",\n".join(values) + ";\n\n"

    sql += f"""-- Verify data integrity
DO $$
DECLARE
    edge_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO edge_count FROM journey_edges;
    RAISE NOTICE 'Journey edges after migration: %', edge_count;

    -- Should have {len(rules)} from CSV + 1 entry edge
    IF edge_count != {len(rules) + 1} THEN
        RAISE WARNING 'Expected {len(rules) + 1} edges but found %', edge_count;
    END IF;
END $$;

COMMIT;
"""

    with open(output_path, 'w') as f:
        f.write(sql)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Generate SQL migration from routing_rules.csv'
    )
    parser.add_argument(
        '--csv',
        type=Path,
        default=Path('config/routing_rules.csv'),
        help='Path to CSV file (default: config/routing_rules.csv)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('migrations'),
        help='Output directory for migration (default: migrations/)'
    )
    parser.add_argument(
        '--number',
        type=int,
        help='Migration number (default: auto-detect next number)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate CSV without generating migration'
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    csv_path = script_dir / args.csv if not args.csv.is_absolute() else args.csv
    output_dir = script_dir / args.output if not args.output.is_absolute() else args.output

    print("╔══════════════════════════════════════════════════╗")
    print("║  Journey Edge Migration Generator                ║")
    print("╚══════════════════════════════════════════════════╝\n")

    if args.dry_run:
        print("🔍 Dry run mode - validating only\n")
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rules = list(reader)

        errors = validate_csv_rules(rules)
        if errors:
            print("❌ Validation errors:\n")
            for error in errors:
                print(f"  • {error}")
            sys.exit(1)
        else:
            print(f"✓ {len(rules)} rules validated successfully")
            sys.exit(0)

    # Generate migration
    output_path = generate_migration(csv_path, output_dir, args.number)

    print(f"\n✓ Generated migration: {output_path.relative_to(Path.cwd())}")
    print(f"✓ Contains {len(list(csv.DictReader(open(csv_path))))} routing rules")

    print("\n" + "=" * 50)
    print("Next steps:")
    print("=" * 50)
    print(f"\n1. Review the generated SQL:")
    print(f"   cat {output_path.relative_to(Path.cwd())}")
    print(f"\n2. Test in development:")
    print(f"   docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey \\")
    print(f"     < {output_path.relative_to(Path.cwd())}")
    print(f"\n3. Verify changes:")
    print(f"   docker exec nvox-postgres psql -U transplant_user -d transplant_journey \\")
    print(f"     -c \"SELECT COUNT(*) FROM journey_edges;\"")
    print(f"\n4. Commit to version control:")
    print(f"   git add {output_path.relative_to(Path.cwd())}")
    print(f"   git commit -m \"Update journey routing edges from CSV\"")
    print()


if __name__ == "__main__":
    main()

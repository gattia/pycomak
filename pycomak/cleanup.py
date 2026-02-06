#!/usr/bin/env python3
"""
Cleanup legacy VTP files from JointMechanics output.

Prior to pycomak 0.6, JointMechanics output ~30,000 VTP files per subject.
The new defaults output only contact surface VTPs (~800 files).
This tool removes the legacy files that are no longer needed.

Files DELETED:
- _ligament_*.vtp  (~9,200 files/subject)
- _muscle_*.vtp    (~4,400 files/subject)
- _mesh_*.vtp      (~16,000 files/subject)

Files KEPT:
- _contact_*.vtp   (~800 files/subject) - cartilage/menisci contact surfaces
- *.h5             - consolidated numerical data
- *.sto            - force/transform data

Usage:
    # Dry run (default) - shows what would be deleted
    pycomak-cleanup --path /path/to/results

    # Actually delete files
    pycomak-cleanup --path /path/to/results --execute
"""

import argparse
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import List, Dict


# Patterns for files to DELETE (legacy VTP outputs)
DELETE_PATTERNS = [
    '_ligament_*.vtp',
    '_muscle_*.vtp',
    '_mesh_*.vtp',
]


def find_joint_mechanics_dirs(base_path: str) -> List[str]:
    """
    Find all joint-mechanics directories under base_path.

    Args:
        base_path: Root directory to search from

    Returns:
        List of paths to joint-mechanics directories
    """
    jm_dirs = []

    # Directories to skip for efficiency
    skip_dirs = {'geometries_nsm_similarity', 'inputs', '.git', '__pycache__'}

    for root, dirs, files in os.walk(base_path):
        if os.path.basename(root) == 'joint-mechanics':
            jm_dirs.append(root)
        # Prune dirs we don't need to descend into
        dirs[:] = [d for d in dirs if d not in skip_dirs]

    return jm_dirs


def delete_files_in_dir(jm_dir: str, dry_run: bool = True) -> Dict:
    """
    Delete legacy VTP files in a joint-mechanics directory.

    Args:
        jm_dir: Path to joint-mechanics directory
        dry_run: If True, only count files without deleting

    Returns:
        Dict with 'deleted' count, 'size_freed' bytes, and 'errors' list
    """
    result = {
        'dir': jm_dir,
        'deleted': 0,
        'size_freed': 0,
        'errors': [],
    }

    for pattern in DELETE_PATTERNS:
        files = glob.glob(os.path.join(jm_dir, pattern))
        for f in files:
            try:
                size = os.path.getsize(f)
                if not dry_run:
                    os.remove(f)
                result['deleted'] += 1
                result['size_freed'] += size
            except OSError as e:
                result['errors'].append(f"{f}: {e}")

    return result


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def cleanup_legacy_vtp_files(
    path: str,
    execute: bool = False,
    workers: int = 8,
    verbose: bool = True,
) -> Dict:
    """
    Clean up legacy VTP files from JointMechanics output.

    Args:
        path: Root directory to search for joint-mechanics folders
        execute: If True, actually delete files. If False, dry-run only.
        workers: Number of parallel workers for file deletion
        verbose: If True, print progress messages

    Returns:
        Dict with summary: 'directories', 'files_deleted', 'size_freed', 'errors'
    """
    dry_run = not execute

    if verbose:
        print("=" * 70)
        print("LEGACY VTP CLEANUP")
        print("=" * 70)
        mode = 'DRY RUN (no files will be deleted)' if dry_run else 'EXECUTE (files will be deleted!)'
        print(f"\nMode: {mode}")
        print(f"Path: {path}")
        print()

    # Find all joint-mechanics directories
    if verbose:
        print("Scanning for joint-mechanics directories...")

    if not os.path.exists(path):
        if verbose:
            print(f"  ERROR: Path does not exist: {path}")
        return {'directories': 0, 'files_deleted': 0, 'size_freed': 0, 'errors': 1}

    jm_dirs = find_joint_mechanics_dirs(path)

    if verbose:
        print(f"  Found: {len(jm_dirs)} directories")

    if not jm_dirs:
        if verbose:
            print("No joint-mechanics directories found. Exiting.")
        return {'directories': 0, 'files_deleted': 0, 'size_freed': 0, 'errors': 0}

    # Process directories
    if verbose:
        action = 'Analyzing' if dry_run else 'Deleting'
        print(f"\n{action} files...")

    start_time = time.time()
    total_deleted = 0
    total_size = 0
    total_errors = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(delete_files_in_dir, jm_dir, dry_run): jm_dir
            for jm_dir in jm_dirs
        }

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            total_deleted += result['deleted']
            total_size += result['size_freed']
            total_errors += len(result['errors'])

            # Progress update every 50 directories
            if verbose and (i % 50 == 0 or i == len(jm_dirs)):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(jm_dirs) - i) / rate if rate > 0 else 0
                print(f"  Progress: {i}/{len(jm_dirs)} dirs | "
                      f"{total_deleted:,} files | {format_size(total_size)} | "
                      f"ETA: {eta:.0f}s")

    elapsed = time.time() - start_time

    # Summary
    if verbose:
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Directories processed: {len(jm_dirs)}")
        action = 'to delete' if dry_run else 'deleted'
        print(f"Files {action}: {total_deleted:,}")
        action = 'to free' if dry_run else 'freed'
        print(f"Space {action}: {format_size(total_size)}")
        print(f"Errors: {total_errors}")
        print(f"Time: {elapsed:.1f}s")

        if dry_run:
            print("\n" + "-" * 70)
            print("This was a DRY RUN. No files were deleted.")
            print("To actually delete files, run with --execute flag")
            print("-" * 70)

    return {
        'directories': len(jm_dirs),
        'files_deleted': total_deleted,
        'size_freed': total_size,
        'errors': total_errors,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Remove legacy VTP files from JointMechanics output.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--path',
        type=str,
        required=True,
        help='Root directory to search for joint-mechanics folders'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete files (default is dry-run)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=8,
        help='Number of parallel workers (default: 8)'
    )
    args = parser.parse_args()

    cleanup_legacy_vtp_files(
        path=args.path,
        execute=args.execute,
        workers=args.workers,
        verbose=True,
    )


if __name__ == '__main__':
    main()

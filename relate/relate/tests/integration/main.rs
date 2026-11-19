//! The `integration` integration-test binary: every test file that can
//! share a process with its siblings, compiled and linked once instead
//! of once per file (scripts/merge-test-binaries.py). A file that
//! mutates the process environment, samples process-wide memory, or
//! re-executes its own binary stays a binary of its own directly under
//! `tests/`. Add a new shareable test file here as a `mod` line; the
//! `every_file_is_declared` test fails on a file left out.

#[path = "../common/mod.rs"]
mod common;

mod aggregate_postfix;
mod aggregate_transparent_positions;
mod argument_error_classes;
mod bar_function;
mod bytes_value;
mod cancellation;
mod canonical_registries;
mod case_expression;
mod checked_int_ops;
mod chronological_comparisons_closed;
mod cip_240_search_filters;
mod cip_subqueries;
mod cip_value_operators;
mod clone;
mod collect_list_concat;
mod comparison_semantics;
mod compile_time_error_classes;
mod complex_search_patterns_closed;
mod constraint_numeric_equivalence;
mod cypher25_dialect;
mod cypher_version_preamble;
mod dbms_procedures;
mod ddl_error_classes;
mod ddl_result_shape;
mod distinct_differential;
mod duration_fraction_truncation;
mod dynamic_operand_validation;
mod equality_postings_serve_labs1731;
mod explain_profile;
mod float16_coordinate_types_closed;
mod fulltext_search_semantics;
mod function_preview_closed;
mod function_registry_gap;
mod gql_for;
mod graph_type;
mod inf_nan_keywords;
mod integer_argument_error_classes;
mod invalid_unicode_character;
mod json_snapshot_recovery;
mod keyword_aliases;
mod keyword_label_names;
mod keyword_symbolic_names;
mod label_disjunction_seek_labs1083;
mod labs156_list_carry;
mod labs157_pattern_anchor;
mod labs193_pattern_exists_probe;
mod labs246_pattern_exists_limit1;
mod labs249_pattern_probe_anonymous_endpoint;
mod labs250_in_list_node_seek;
mod labs255_258_expansion_order;
mod labs273_stats_orientation;
mod labs286_engine_elapsed;
mod labs290_column_types;
mod labs366_seek_right_property_in;
mod labs367_path_fold_pred_row_scope;
mod labs418_envelope_plan;
mod labs610_traversal_depth;
mod labs646_corpus_engine_pins;
mod labs680_safe_mode;
mod labs801_reltype_ids;
mod labs832_phase_envelope;
mod load_csv;
mod markdown_vault_e2e;
mod match_shape_validation;
mod misc_tail_forms;
mod notifications;
mod order_by_top_k_bounds;
mod parameter_missing;
mod parquet_wide_format_facade;
mod parser_syntax_gap_regressions;
mod pattern_predicates;
mod pattern_prop_policy;
mod point_index;
mod pokec_fixture;
mod predicate_list_coercion;
mod procedure_validation;
mod profile_frontier_metrics;
mod profile_kernel_rung;
mod profile_metrics;
mod profile_warnings;
mod projection_paren_transparency;
mod property_index_numeric_equivalence;
mod publish_race;
mod read_only;
mod recovery_fails_closed;
mod return_item_column_names;
mod return_sharing;
mod round_precision;
mod run_script;
mod scalar_function_arity;
mod scalar_function_live_parity;
mod schema_procedures;
mod sealed_adjacency_reopen;
mod show_catalog_shape;
mod show_commands;
mod show_indexes_create_statement;
mod source_unicode_escapes;
mod spatial_argument_error_classes;
mod statement_notifications;
mod statement_notifications_dynamic_property;
mod statement_notifications_hints;
mod statement_notifications_optional;
mod statement_notifications_shapes;
mod string_arg_checks;
mod string_index_lazy;
mod subclause_aggregation;
mod temporal_constructor_arity;
mod temporal_identity_split;
mod temporal_map_field_policy;
mod temporal_pattern_safety;
#[allow(non_snake_case)]
mod toString_path_display;
mod to_integer_error_classes;
mod type_error_classes;
mod typed_ir_exprs;
mod undefined_variable;
mod unicode_identifiers;
mod uuid_label_predicates;
mod vector_quantization_type;
mod vector_search_candidates;
mod write_effect;
mod write_validation;

/// A file under this directory that no `mod` line declares would
/// silently never compile or run.
#[test]
fn every_file_is_declared() {
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/integration");
    let main = include_str!("main.rs");
    for entry in std::fs::read_dir(&dir).expect("test directory is readable") {
        let path = entry.expect("directory entry is readable").path();
        if path.extension().is_some_and(|ext| ext == "rs") {
            let stem = path.file_stem().unwrap().to_str().unwrap();
            if stem != "main" {
                assert!(
                    main.contains(&format!("\nmod {stem};\n")),
                    "tests/integration/{stem}.rs is not declared in main.rs"
                );
            }
        }
    }
}

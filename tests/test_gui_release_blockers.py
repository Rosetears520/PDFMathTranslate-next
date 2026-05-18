import sys
import tempfile
from pathlib import Path

import pytest
from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel


def _gui(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pytest"])
    import pdf2zh_next.gui as gui

    return gui


def _empty_state():
    return {
        "session_id": None,
        "current_task": None,
        "results": {},
        "file_order": [],
        "display_map": {},
        "parent_map": {},
        "uploaded_files": [],
    }


def _base_gui_inputs():
    return {
        "service": "SiliconFlowFree",
        "lang_from": "English",
        "lang_to": "Simplified Chinese",
        "page_range": "All",
        "page_input": "",
        "prompt": "",
        "ignore_cache": False,
        "no_mono": False,
        "no_dual": False,
        "dual_translate_first": False,
        "use_alternating_pages_dual": False,
        "watermark_output_mode": "No Watermark",
        "rate_limit_mode": "Custom",
        "custom_qps": 4,
        "custom_pool_workers": None,
        "min_text_length": 5,
        "rpc_doclayout": "",
        "enable_auto_term_extraction": False,
        "primary_font_family": "Auto",
        "skip_clean": False,
        "disable_rich_text_translate": False,
        "enhance_compatibility": False,
        "split_short_lines": False,
        "short_line_split_factor": 0.8,
        "translate_table_text": False,
        "skip_scanned_detection": False,
        "ocr_workaround": False,
        "max_pages_per_part": 0,
        "formular_font_pattern": "",
        "formular_char_pattern": "",
        "auto_enable_ocr_workaround": False,
        "only_include_translated_page": False,
        "merge_alternating_line_numbers": True,
        "remove_non_formula_lines": True,
        "non_formula_line_iou_threshold": 0.5,
        "figure_table_protection_threshold": 0.5,
        "skip_formula_offset_calculation": False,
        "term_service": "Follow main translation engine",
        "term_rate_limit_mode": "Custom",
        "term_rpm_input": 240,
        "term_concurrent_threads": 20,
        "term_custom_qps": 4,
        "term_custom_pool_workers": None,
        "custom_system_prompt_input": "",
        "glossaries": None,
        "save_auto_extracted_glossary": False,
        "siliconflow_free_enable_json_mode": False,
    }


def test_pdf_preview_allowed_paths_exclude_broad_filesystem_paths(monkeypatch):
    gui = _gui(monkeypatch)

    allowed_paths = [Path(path).resolve() for path in gui.pdf_preview_allowed_paths]
    root_paths = {Path(path.anchor).resolve() for path in allowed_paths if path.anchor}

    assert Path.cwd().resolve() not in allowed_paths
    assert Path.home().resolve() not in allowed_paths
    assert not root_paths.intersection(allowed_paths)


def test_pdf_preview_allowed_paths_keep_accepted_preview_locations(monkeypatch):
    gui = _gui(monkeypatch)

    allowed_paths = [Path(path).resolve() for path in gui.pdf_preview_allowed_paths]
    expected_paths = {
        gui.logo_path.resolve(),
        Path("pdf2zh_files").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    }

    assert set(allowed_paths) == expected_paths


def test_on_file_upload_empty_list_returns_all_declared_outputs(monkeypatch):
    gui = _gui(monkeypatch)
    state = _empty_state()

    result = gui.on_file_upload([], state)

    assert len(result) == 3
    assert result[0]["choices"] == []
    assert result[0]["value"] is None
    assert result[0]["visible"] is False
    assert result[1] is state
    assert result[2]["value"] == ""
    assert result[2]["visible"] is False


def test_on_file_upload_none_returns_all_declared_outputs(monkeypatch):
    gui = _gui(monkeypatch)
    state = _empty_state()

    result = gui.on_file_upload(None, state)

    assert len(result) == 3
    assert result[0]["choices"] == []
    assert result[0]["value"] is None
    assert result[0]["visible"] is False
    assert result[1] is state
    assert result[2]["value"] == ""
    assert result[2]["visible"] is False


@pytest.mark.parametrize("save_mode_name", ["always", "follow_settings"])
def test_build_translate_settings_preserves_current_gui_language_on_save(
    tmp_path, monkeypatch, save_mode_name
):
    gui = _gui(monkeypatch)
    captured_settings = []

    def capture_user_config(settings):
        captured_settings.append(settings.clone())

    monkeypatch.setattr(
        gui.config_manager,
        "write_user_default_config_file",
        capture_user_config,
    )
    startup_settings = gui.config_manager.config_cli_settings.clone()
    startup_settings.gui_settings.ui_lang = "en"
    monkeypatch.setattr(gui.config_manager, "config_cli_settings", startup_settings)

    current_settings = CLIEnvSettingsModel()
    current_settings.gui_settings.ui_lang = "zh"
    current_settings.gui_settings.disable_config_auto_save = False
    monkeypatch.setattr(gui, "settings", current_settings.clone())

    input_pdf = tmp_path / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    gui._build_translate_settings(
        current_settings,
        input_pdf,
        output_dir,
        getattr(gui.SaveMode, save_mode_name),
        _base_gui_inputs(),
    )

    assert len(captured_settings) == 1
    assert captured_settings[0].gui_settings.ui_lang == "zh"
    assert gui.settings.gui_settings.ui_lang == "zh"

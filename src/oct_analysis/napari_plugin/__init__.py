def main():
    from oct_analysis.napari_plugin import widgets
    from qtpy.QtWidgets import QScrollArea, QWidget, QVBoxLayout
    from magicgui.widgets import Container
    from magicgui import magicgui
    import json
    from pathlib import Path

    widget_list = [
        widgets.show_instructions,
        widgets.load_oct,
        widgets.median_filter,
        widgets.roi_filter_2D,
        widgets.locate_window,
        widgets.zero_out_window,
        widgets.locate_substratum,
        widgets.zero_out_substratum,
        widgets.increase_contrast,
        widgets.binarize,
        widgets.remove_outliers,
        widgets.save
    ]

    # save-settings funktion. später ersetzen durch class-struktur des widgets.py inhalts
    @magicgui(call_button="Save Settings",
            settings_file={"widget_type": "FileEdit", "mode": "w", "value": str(Path.home() / "settings.json")}
    )
    def save_settings(settings_file):
        settings = {}
        for widget in widget_list:
            params = {}
            # Die ursprünglichen Parameter stehen in __signature__.parameters
            for param in widget.__signature__.parameters:
                if param == "viewer":
                    continue  # viewer ist nicht serialisierbar
                w = widget.get_widget(param)
                if w is not None:
                    val = w.value
                    if isinstance(val, Path):
                        val = str(val)
                    params[param] = val
            settings[widget.name or widget.__class__.__name__] = params

        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=4)
    #

    all_widgets = Container(
        widgets=widget_list + [save_settings],
        layout='vertical',
        name='Image Processing Tools',
        visible=True,
        labels=False
    )

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    container_widget = QWidget()
    layout = QVBoxLayout(container_widget)
    layout.addWidget(all_widgets.native)
    scroll.setWidget(container_widget)
    scroll.setMinimumWidth(400)

    return scroll

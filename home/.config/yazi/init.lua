-- require("full-border"):setup({
-- 	-- Available values: ui.Border.PLAIN, ui.Border.ROUNDED
-- 	type = ui.Border.ROUNDED,
-- })

require("yatline"):setup({
	header_line = {},

	status_line = {
		left = {
			section_a = {
				{ type = "string", custom = false, name = "tab_mode" },
			},
			section_b = {
				{ type = "string", custom = false, name = "hovered_size" },
			},
			section_c = {
				{ type = "string", custom = false, name = "hovered_name" },
			},
		},
		right = {
			section_a = {
				{ type = "string", custom = false, name = "cursor_position" },
			},
			section_b = {
				{ type = "string", custom = false, name = "cursor_percentage" },
			},
			section_c = {
				{ type = "coloreds", custom = false, name = "permissions" },
			},
		},
	},
})

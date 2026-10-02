return {
	{
		"bjarneo/aether.nvim",
		branch = "v3",
		name = "aether",
		priority = 1000,
		opts = {
			colors = {
				bg = "#16242d",
				dark_bg = "#101b21",
				darker_bg = "#0b1216",
				lighter_bg = "#1b2d40",

				fg = "#d6e2ee",
				dark_fg = "#4d86b0",
				light_fg = "#d6e2ee",
				bright_fg = "#f2fcff",
				muted = "#848C93",

				red = "#4d86b0",
				yellow = "#6fa4c9",
				orange = "#8bc9eb",
				green = "#5e95bc",
				cyan = "#6fb8e3", --#b4e4f6
				blue = "#6fb8e3",
				magenta = "#8bc9eb",
				brown = "#456475",

				bright_red = "#73a6cb",
				bright_yellow = "#9dcae5",
				bright_green = "#86b7d8",
				bright_cyan = "#f2fcff",
				bright_blue = "#f2fcff",
				bright_magenta = "#b1d8ee",

				accent = "#8bc9eb",
				cursor = "#f2fcff",
				foreground = "#d6e2ee",
				background = "#16242d",
				selection = "#243d56",
				selection_foreground = "#73a6cb",
				selection_background = "#1b2d40",
			},
		},
	},
	{
		"LazyVim/LazyVim",
		opts = {
			colorscheme = "aether",
		},
	},
}

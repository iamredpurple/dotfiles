return {
  {
    "bjarneo/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      colors = {
        bg = "#101417",
        dark_bg = "#1c2024",
        darker_bg = "#181c20",
        lighter_bg = "#313539",

        fg = "#e0e3e8",
        dark_fg = "#c1c7ce",
        light_fg = "#41474d",
        bright_fg = "#004b6f",
        muted = "#8b9198",

        red = "#ffb4ab",
        yellow = "#cfc0e8",
        orange = "#eaddff",
        green = "#b7c9d9",
        cyan = "#95cdf7", -- or #d3e5f5
        blue = "#95cdf7",
        magenta = "#266489",
        brown = "#4c4162",

        bright_red = "#ffb4ab",
        bright_yellow = "#eaddff",
        bright_green = "#d3e5f5",
        bright_cyan = "#95cdf7", -- or #c9e6ff
        bright_blue = "#95cdf7",
        bright_magenta = "#b7c9d9",

        accent = "#95cdf7",
        cursor = "#004b6f",
        foreground = "#e0e3e8",
        background = "#101417",
        selection = "#262a2e",
        selection_foreground = "#c1c7ce",
        selection_background = "#313539",
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

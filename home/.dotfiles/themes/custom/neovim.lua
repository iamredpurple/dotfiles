return {
  {
    "bjarneo/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      colors = {
        bg = "#1a1111",
        dark_bg = "#271d1d",
        darker_bg = "#231919",
        lighter_bg = "#3d3231",

        fg = "#f1dedd",
        dark_fg = "#d8c2bf",
        light_fg = "#534342",
        bright_fg = "#733330",
        muted = "#a08c8a",

        red = "#ffb4ab",
        yellow = "#e2c28c",
        orange = "#ffdea6",
        green = "#e7bdb9",
        cyan = "#ffb3ae", -- or #ffdad7
        blue = "#ffb3ae",
        magenta = "#904a46",
        brown = "#594319",

        bright_red = "#ffb4ab",
        bright_yellow = "#ffdea6",
        bright_green = "#ffdad7",
        bright_cyan = "#ffb3ae", -- or #ffdad7
        bright_blue = "#ffb3ae",
        bright_magenta = "#e7bdb9",

        accent = "#ffb3ae",
        cursor = "#733330",
        foreground = "#f1dedd",
        background = "#1a1111",
        selection = "#322827",
        selection_foreground = "#d8c2bf",
        selection_background = "#3d3231",
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

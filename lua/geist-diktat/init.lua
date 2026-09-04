-- geist-diktat.nvim — dictation at the cursor via job-control.
--
-- No keystroke injection: transcript lines from the diktat pipeline are
-- put into the buffer programmatically (nvim_put), so vim's modal editing
-- is never confused by dictated text.

local M = {}

local defaults = {
    -- Full pipeline command. nil = built from binary/model/rms below.
    cmd = nil,
    binary = "diktat",
    model = (os.getenv("XDG_DATA_HOME") or (os.getenv("HOME") .. "/.local/share"))
        .. "/geist-diktat/gemma4-e2b-Q4_K_M.gguf",
    rms = 300,
    -- Inserted after each utterance (dictated text flows like typing).
    suffix = " ",
}

-- Effective configuration; :checkhealth reads it instead of re-deriving
-- the defaults.
M.opts = vim.deepcopy(defaults)
local job = nil
local queued = {}

function M.setup(user_opts)
    M.opts = vim.tbl_deep_extend("force", vim.deepcopy(defaults), user_opts or {})
end

local function pipeline_cmd()
    if M.opts.cmd then
        return M.opts.cmd
    end
    return ("arecord -q -f S16_LE -r 16000 -c 1 -t raw | %s %s %d"):format(
        M.opts.binary,
        vim.fn.shellescape(M.opts.model),
        M.opts.rms
    )
end

-- Put one utterance at the cursor. In command-line mode putting would
-- error; queue and flush once the mode is safe again.
local function put_line(text)
    local mode = vim.api.nvim_get_mode().mode
    if mode:sub(1, 1) == "c" then
        table.insert(queued, text)
        return
    end
    for _, t in ipairs(queued) do
        pcall(vim.api.nvim_put, { t .. M.opts.suffix }, "c", true, true)
    end
    queued = {}
    pcall(vim.api.nvim_put, { text .. M.opts.suffix }, "c", true, true)
end

function M.start()
    if job then
        vim.notify("geist-diktat: already listening", vim.log.levels.INFO)
        return
    end
    job = vim.fn.jobstart({ "sh", "-c", pipeline_cmd() }, {
        on_stdout = function(_, lines, _)
            for _, line in ipairs(lines) do
                if line ~= "" then
                    vim.schedule(function()
                        put_line(line)
                    end)
                end
            end
        end,
        on_exit = function(_, code, _)
            job = nil
            vim.g.geist_diktat_active = false
            if code ~= 0 then
                vim.schedule(function()
                    vim.notify("geist-diktat: pipeline exited (" .. code .. ")", vim.log.levels.WARN)
                end)
            end
        end,
    })
    if job <= 0 then
        job = nil
        vim.notify("geist-diktat: failed to start pipeline", vim.log.levels.ERROR)
        return
    end
    vim.g.geist_diktat_active = true
    vim.notify("geist-diktat: listening", vim.log.levels.INFO)
end

function M.stop()
    if not job then
        return
    end
    vim.fn.jobstop(job) -- kills the process group: arecord goes down with it
    job = nil
    vim.g.geist_diktat_active = false
    vim.notify("geist-diktat: stopped", vim.log.levels.INFO)
end

function M.toggle()
    if job then
        M.stop()
    else
        M.start()
    end
end

function M.is_active()
    return job ~= nil
end

return M

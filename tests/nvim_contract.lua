-- Real Neovim buffers; deterministic job callbacks for race/mode regressions.
local failures, count = 0, 0
local function check(name, fn)
  count = count + 1
  local ok, err = pcall(fn)
  io.stdout:write((ok and 'PASS ' or 'FAIL ') .. name .. (ok and '' or ': ' .. tostring(err)) .. '\n')
  if not ok then failures = failures + 1 end
end
local real_start, real_stop = vim.fn.jobstart, vim.fn.jobstop
local real_mode = vim.api.nvim_get_mode
local jobs, current, mode = {}, 0, 'n'
vim.notify = function() end
local function fresh(opts)
  package.loaded['geist-diktat'] = nil
  vim.cmd('enew!')
  mode = 'n'
  vim.api.nvim_get_mode = function() return {mode=mode} end
  vim.fn.jobstart = function(cmd, cb)
    current = current + 1
    jobs[current] = {cmd=cmd, cb=cb}
    return current
  end
  vim.fn.jobstop = function() return 1 end
  local m = require('geist-diktat')
  m.setup(opts or {cmd='stub'})
  m.start()
  return m, current
end
local function output(id, lines)
  jobs[id].cb.on_stdout(id, lines, 'stdout')
  vim.wait(20, function() return false end)
end
local function text() return table.concat(vim.api.nvim_buf_get_lines(0,0,-1,false),'\n') end
check('complete Unicode line', function()
  local _, id=fresh(); output(id, {'Grüße 世界',''}); assert(text()=='Grüße 世界 ')
end)
check('blank lines ignored', function()
  local _, id=fresh(); output(id, {'','',''}); assert(text()=='')
end)
check('fragmented stdout reassembled', function()
  local _, id=fresh(); output(id, {'hel'}); output(id, {'lo',''}); assert(text()=='hello ',text())
end)
check('split UTF-8 reassembled', function()
  local _, id=fresh(); output(id, {string.char(195)}); output(id, {string.char(188),''}); assert(text()=='ü ',vim.inspect(text()))
end)
check('custom suffix', function()
  local _, id=fresh({cmd='stub',suffix='.'}); output(id, {'hello',''}); assert(text()=='hello.')
end)
check('duplicate start ignored', function()
  local m,id=fresh(); m.start(); assert(current==id)
end)
check('exit clears active state', function()
  local m,id=fresh(); jobs[id].cb.on_exit(id,0,'exit'); assert(not m.is_active())
end)
check('old exit cannot stop restarted job', function()
  local m,id=fresh(); m.stop(); m.start(); jobs[id].cb.on_exit(id,143,'exit'); assert(m.is_active())
end)
check('late stdout after stop discarded', function()
  local m,id=fresh(); m.stop(); output(id,{'late',''}); assert(text()=='',text())
end)
check('command-line queue flushes when leaving mode', function()
  local _,id=fresh(); mode='c'; output(id,{'queued',''}); assert(text()=='')
  mode='n'; vim.api.nvim_exec_autocmds('ModeChanged',{pattern='c:n'})
  vim.wait(30,function() return false end); assert(text()=='queued ',text())
end)
check('stopped queue never leaks into next session', function()
  local m,id=fresh(); mode='c'; output(id,{'old',''}); m.stop(); mode='n'; m.start()
  output(current,{'new',''}); assert(text()=='new ',text())
end)
check('binary path shell-quoted', function()
  local _,id=fresh({binary='/tmp/dictation tools/diktat',model="/tmp/model with ' quote.gguf"})
  assert(jobs[id].cmd[3]:find(vim.fn.shellescape('/tmp/dictation tools/diktat'),1,true))
end)
check('read-only buffer reports lost insertion', function()
  local _,id=fresh(); local messages={}; vim.notify=function(s) table.insert(messages,s) end
  vim.bo.modifiable=false; output(id,{'lost',''}); vim.bo.modifiable=true
  assert(#messages>0,'pcall swallows insertion failure')
end)
vim.fn.jobstart, vim.fn.jobstop = real_start, real_stop
vim.api.nvim_get_mode = real_mode
io.stdout:write(('TOTAL %d FAILED %d\n'):format(count,failures))
vim.cmd(failures==0 and 'qa!' or 'cquit')

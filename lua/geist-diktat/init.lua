-- One generation owns every callback, partial UTF-8 line and queued insertion.
local M = {}
local defaults = {cmd=nil, launcher='geist-diktat', rms=300, suffix=' ', max_pending_bytes=65536}
M.opts = vim.deepcopy(defaults)
local active, generation = nil, 0
local function notify(message) vim.notify('geist-diktat: '..message,vim.log.levels.WARN) end
local function valid(s) return generation==s.generation and not s.cancelled end
local function flush(s)
  if not valid(s) then return end
  if vim.api.nvim_get_mode().mode:sub(1,1)=='c' then return end
  if not vim.api.nvim_buf_is_valid(s.buffer) or vim.api.nvim_get_current_buf()~=s.buffer then
    if #s.queued>0 then notify('target buffer changed; pending text discarded') end
    s.queued={};s.bytes=0;return
  end
  local queued=s.queued;s.queued={};s.bytes=0
  for _,text in ipairs(queued) do
    local ok,err=pcall(vim.api.nvim_put,{text..M.opts.suffix},'c',true,true)
    if not ok then notify('text could not be inserted: '..tostring(err)) end
  end
end
local function enqueue(s,line)
  if not valid(s) or line=='' then return end
  if s.bytes+#line>M.opts.max_pending_bytes then
    notify('pending text limit exceeded; dictation stopped');M.stop();return
  end
  s.queued[#s.queued+1]=line;s.bytes=s.bytes+#line
  vim.schedule(function() flush(s) end)
end
local function command()
  if M.opts.cmd then return type(M.opts.cmd)=='table' and M.opts.cmd or {'sh','-c',M.opts.cmd} end
  local parts={'exec env'}
  if M.opts.binary then parts[#parts+1]='GEIST_DIKTAT_CORE='..vim.fn.shellescape(M.opts.binary) end
  if M.opts.model then parts[#parts+1]='GEIST_DIKTAT_MODEL='..vim.fn.shellescape(M.opts.model) end
  parts[#parts+1]=vim.fn.shellescape(M.opts.launcher)
  parts[#parts+1]='run';parts[#parts+1]=vim.fn.shellescape(tostring(M.opts.rms))
  return {'sh','-c',table.concat(parts,' ')}
end
function M.setup(opts)
  if active then M.stop() end
  M.opts=vim.tbl_deep_extend('force',vim.deepcopy(defaults),opts or {})
end
function M.start()
  if active and active.job then return end
  generation=generation+1
  local s={generation=generation,partial='',queued={},bytes=0,buffer=vim.api.nvim_get_current_buf()}
  active=s
  local group=vim.api.nvim_create_augroup('GeistDiktatInsertion',{clear=true})
  vim.api.nvim_create_autocmd('ModeChanged',{group=group,callback=function() vim.schedule(function() flush(s) end) end})
  s.job=vim.fn.jobstart(command(),{
    on_stdout=function(_,lines)
      if not valid(s) then return end
      for i,line in ipairs(lines) do
        s.partial=s.partial..line
        if #s.partial>M.opts.max_pending_bytes then notify('invalid oversized transcript');M.stop();return end
        if i<#lines then enqueue(s,s.partial);s.partial='' end
      end
    end,
    on_stderr=function(_,lines)
      if not valid(s) then return end
      for _,line in ipairs(lines) do
        if line:find('overload:',1,true) or line:find('failed',1,true) then
          vim.schedule(function() if valid(s) then notify(line) end end)
        end
      end
    end,
    on_exit=function(_,code)
      if not valid(s) then return end
      -- EOF is a complete final fragment; stop/cancel deliberately drops it.
      if s.partial~='' then enqueue(s,s.partial);s.partial='' end
      s.job=nil;vim.g.geist_diktat_active=false
      if code~=0 then vim.schedule(function() if valid(s) then notify('pipeline exited ('..code..')') end end) end
    end,
  })
  if s.job<=0 then s.job=nil;s.cancelled=true;notify('failed to start pipeline');return end
  vim.g.geist_diktat_active=true
end
function M.stop()
  local s=active
  generation=generation+1;active=nil;vim.g.geist_diktat_active=false
  if s then
    s.cancelled=true;s.queued={};s.partial='';s.bytes=0
    if s.job then vim.fn.jobstop(s.job);s.job=nil end
  end
end
function M.toggle() if M.is_active() then M.stop() else M.start() end end
function M.is_active() return active~=nil and active.job~=nil end
return M

-- Read-only synchronous snapshot at the completed real OOP update.
-- No pause, writes, input, queue control, IO-library permission, or ROM patch.
local done = @DONE_OFFSET@
local ranges = {@RANGES@}
local sequence = 0
local diagnosticObjSel = @DIAGNOSTIC_OBJSEL@
local objSelWritten = false
local function traceObj(address, value)
    local fields = {}
    for key, v in pairs(emu.getState()) do
        local k = string.lower(key)
        if k == "cpu.pc" or k == "cpu.k" or k == "cpu.d" or k == "cpu.dbr"
           or k == "ppu.oambaseaddress" or k == "ppu.oammode" then
            fields[#fields + 1] = key .. "=" .. tostring(v)
        end
    end
    table.sort(fields)
    emu.log("S5OBJWRITE|" .. address .. "|" .. value .. "|" .. table.concat(fields, ";"))
end
-- Physical WRAM catches bank mirrors; hardware accesses are CPU-bus mapped.
emu.addMemoryCallback(traceObj, emu.callbackType.write, @OBJ_SHADOW_OFFSET@,
                      @OBJ_SHADOW_OFFSET@, emu.cpuType.snes, emu.memType.snesWorkRam)
emu.addMemoryCallback(traceObj, emu.callbackType.write, 0x2101, 0x2101,
                      emu.cpuType.snes, emu.memType.snesMemory)
emu.addMemoryCallback(traceObj, emu.callbackType.write, 0x802101, 0x802101,
                      emu.cpuType.snes, emu.memType.snesMemory)
local heartbeat = 0
emu.addEventCallback(function()
    heartbeat = heartbeat + 1
    if heartbeat <= 3 then emu.log("S5LUA_FRAME|" .. heartbeat) end
end, emu.eventType.endFrame)
local function capture(address, value)
    sequence = sequence + 1
    local parts = {"S5COMMIT", tostring(sequence), tostring(address)}
    for _, range in ipairs(ranges) do
        local bytes = {}
        for p = range[1], range[1] + range[2] - 1 do
            bytes[#bytes + 1] = string.format("%02x", emu.read(p, emu.memType.snesMemory))
        end
        parts[#parts + 1] = table.concat(bytes)
    end
    local registers = {}
    for key, v in pairs(emu.getState()) do
        local k = string.lower(key)
        if string.find(k, "ppu", 1, true) and
           (string.find(k, "oam", 1, true) or string.find(k, "mode1bg3priority", 1, true)
            or string.find(k, "colormath", 1, true) or string.find(k, "clip", 1, true)
            or string.find(k, "mainscreen", 1, true)) then
            registers[#registers + 1] = key .. "=" .. tostring(v)
        end
    end
    table.sort(registers)
    parts[#parts + 1] = table.concat(registers, ";")
    -- Mesen MCP explicitly routes emu.log to stderr, drained by McpSession.
    emu.log(table.concat(parts, "|"))
    if diagnosticObjSel and not objSelWritten and emu.read16(@NMI_FRAME@, emu.memType.snesMemory) >= 190 then
        -- Explicitly authorized causal probe only; default generated script is
        -- read-only. Lua's bus write enables MMIO side effects (unlike SDK write).
        emu.write(0x2101, 0xC2, emu.memType.snesMemory)
        objSelWritten = true
        emu.log("S5OBJ_CAUSAL_WRITE_C2")
    end
end
emu.addMemoryCallback(capture, emu.callbackType.exec, done, done,
                      emu.cpuType.snes, emu.memType.snesPrgRom)

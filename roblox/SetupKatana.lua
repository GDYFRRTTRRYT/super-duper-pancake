--[[
	King of the Nine Moons - one-shot setup for Roblox Studio.

	1. File > Import 3D > models/KingOfTheNineMoons.obj
	   (turn OFF "Import as single mesh", scale unit = Stud).
	2. Select the imported model in the Explorer.
	3. Paste this whole file into the Command Bar (View > Command Bar) and press Enter.

	The model is converted into a ready-to-use Tool in StarterPack with materials,
	glow, particles, slash trails, an orbiting moon halo and a combat script.
]]

local Selection = game:GetService("Selection")

local model = Selection:Get()[1]
assert(model and (model:IsA("Model") or model:IsA("Folder")), "Select the imported katana model first")

local GOLD = Color3.fromRGB(242, 189, 66)
local MOON = Color3.fromRGB(178, 235, 255)
local VIOLET = Color3.fromRGB(170, 100, 255)

-- Halo spin axis in model space; must match HALO_TILT in tools/generate_katana.py
local HALO_AXIS = Vector3.new(math.sin(math.rad(35)), math.cos(math.rad(35)), 0)

-- name = { color, material, reflectance, transparency }
local STYLE = {
	Blade = { Color3.fromRGB(26, 28, 48), Enum.Material.Metal, 0.35, 0 },
	Hamon = { Color3.fromRGB(189, 214, 255), Enum.Material.Metal, 0.6, 0 },
	EdgeGlow = { Color3.fromRGB(204, 242, 255), Enum.Material.Neon, 0, 0 },
	Vein = { VIOLET, Enum.Material.Neon, 0, 0 },
	Moons = { MOON, Enum.Material.Neon, 0, 0 },
	Habaki = { GOLD, Enum.Material.Metal, 0.3, 0 },
	MoonGuard = { GOLD, Enum.Material.Metal, 0.35, 0 },
	Tsuba = { Color3.fromRGB(33, 28, 56), Enum.Material.Metal, 0.15, 0 },
	GuardRim = { GOLD, Enum.Material.Metal, 0.3, 0 },
	MoonOrbs = { MOON, Enum.Material.Neon, 0, 0 },
	Fuchi = { GOLD, Enum.Material.Metal, 0.3, 0 },
	Tsuka = { Color3.fromRGB(219, 219, 235), Enum.Material.Sand, 0, 0 },
	Ito = { Color3.fromRGB(56, 26, 102), Enum.Material.Fabric, 0, 0 },
	Kashira = { GOLD, Enum.Material.Metal, 0.3, 0 },
	CrownGem = { Color3.fromRGB(184, 92, 255), Enum.Material.Neon, 0, 0 },
	MoonAura = { Color3.fromRGB(140, 128, 255), Enum.Material.Neon, 0, 0.45 },
	MoonHalo = { MOON, Enum.Material.Neon, 0, 0.1 },
}

local parts = {}
for _, inst in model:GetDescendants() do
	if inst:IsA("BasePart") then
		for name in STYLE do
			-- the importer may append suffixes, so fall back to a prefix match
			if inst.Name == name or (not parts[name] and inst.Name:sub(1, #name) == name) then
				parts[name] = inst
			end
		end
	end
end
for name in STYLE do
	assert(parts[name], "Missing mesh part: " .. name .. " (was the OBJ imported as separate meshes?)")
end

local tool = Instance.new("Tool")
tool.Name = "King of the Nine Moons"
tool.ToolTip = "Nine moons obey their king"
tool.CanBeDropped = false
tool.RequiresHandle = true

-- Invisible grip part: its +Y is the blade direction and -Z faces the cutting edge.
local handle = Instance.new("Part")
handle.Name = "Handle"
handle.Size = Vector3.new(0.3, 1, 0.3)
handle.Transparency = 1
handle.CanCollide = false
handle.Massless = true
handle.CFrame = parts.Tsuka.CFrame * CFrame.new(0, 0.3, 0) * CFrame.Angles(0, math.pi, 0)
handle.Parent = tool

local blade = parts.Blade

for name, part in parts do
	local style = STYLE[name]
	part.Name = name
	part.Color = style[1]
	part.Material = style[2]
	part.Reflectance = style[3]
	part.Transparency = style[4]
	part.Anchored = false
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = name == "Blade"
	part.Massless = true
	part.CastShadow = style[2] ~= Enum.Material.Neon
	part.Parent = tool

	if name == "MoonHalo" then
		-- a real Weld so the combat script can spin the halo around its own axis
		local weld = Instance.new("Weld")
		weld.Name = "HaloWeld"
		weld.Part0 = handle
		weld.Part1 = part
		weld.C0 = handle.CFrame:ToObjectSpace(part.CFrame)
		weld.Parent = part
		part:SetAttribute("SpinAxis", part.CFrame:VectorToObjectSpace(blade.CFrame:VectorToWorldSpace(HALO_AXIS)))
	else
		local weld = Instance.new("WeldConstraint")
		weld.Part0 = handle
		weld.Part1 = part
		weld.Parent = part
	end
end

local size = blade.Size

-- Slash trails: the tip curves towards -Z, the cutting edge faces +Z.
local function attachment(name, position)
	local att = Instance.new("Attachment")
	att.Name = name
	att.Position = position
	att.Parent = blade
	return att
end

local base = attachment("TrailBase", Vector3.new(0, -size.Y * 0.40, size.Z * 0.2))
local mid = attachment("TrailMid", Vector3.new(0, size.Y * 0.15, 0))
local tip = attachment("TrailTip", Vector3.new(0, size.Y * 0.5, -size.Z * 0.5 + 0.08))

local function slashTrail(name, a0, a1, lifetime, colors)
	local trail = Instance.new("Trail")
	trail.Name = name
	trail.Attachment0 = a0
	trail.Attachment1 = a1
	trail.Lifetime = lifetime
	trail.MinLength = 0.05
	trail.LightEmission = 1
	trail.FaceCamera = false
	trail.Color = colors
	trail.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.1),
		NumberSequenceKeypoint.new(0.6, 0.6),
		NumberSequenceKeypoint.new(1, 1),
	})
	trail.WidthScale = NumberSequence.new(1, 0.2)
	trail.Enabled = false
	trail.Parent = blade
	return trail
end

slashTrail("SlashTrail", base, tip, 0.32, ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.new(1, 1, 1)),
	ColorSequenceKeypoint.new(0.35, MOON),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(110, 60, 255)),
}))
slashTrail("SlashCore", mid, tip, 0.16, ColorSequence.new(Color3.new(1, 1, 1), MOON))

local function emitter(name, rate)
	local e = Instance.new("ParticleEmitter")
	e.Name = name
	e.Rate = rate
	e.Lifetime = NumberRange.new(0.8, 1.6)
	e.Speed = NumberRange.new(0.3, 1.2)
	e.SpreadAngle = Vector2.new(180, 180)
	e.Acceleration = Vector3.new(0, 1.5, 0)
	e.Rotation = NumberRange.new(0, 360)
	e.RotSpeed = NumberRange.new(-90, 90)
	e.LightEmission = 1
	e.Size = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.05),
		NumberSequenceKeypoint.new(0.3, 0.3),
		NumberSequenceKeypoint.new(1, 0),
	})
	e.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.2),
		NumberSequenceKeypoint.new(1, 1),
	})
	e.Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(150, 110, 255))
	e.Parent = blade
	return e
end

emitter("MoonDust", 16)

-- violet embers that fall away from the blade
local embers = emitter("MoonEmbers", 8)
embers.Color = ColorSequence.new(VIOLET, Color3.fromRGB(70, 40, 200))
embers.Acceleration = Vector3.new(0, -2.5, 0)
embers.Lifetime = NumberRange.new(1.2, 2.2)
embers.Drag = 1

local burst = emitter("MoonBurst", 0)
burst.Speed = NumberRange.new(6, 16)
burst.Lifetime = NumberRange.new(0.3, 0.8)
burst.Drag = 3

local haloSparks = emitter("HaloSparks", 10)
haloSparks.Parent = parts.MoonHalo
haloSparks.Speed = NumberRange.new(0.1, 0.5)
haloSparks.Lifetime = NumberRange.new(0.5, 1)

local light = Instance.new("PointLight")
light.Name = "MoonLight"
light.Color = MOON
light.Brightness = 1.5
light.Range = 10
light.Parent = blade

local gemLight = Instance.new("PointLight")
gemLight.Name = "GemLight"
gemLight.Color = VIOLET
gemLight.Brightness = 1
gemLight.Range = 5
gemLight.Parent = parts.CrownGem

local combat = Instance.new("Script")
combat.Name = "KatanaServer"
combat.Source = [==[
local Debris = game:GetService("Debris")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local tool = script.Parent
local blade = tool:WaitForChild("Blade")
local halo = tool:WaitForChild("MoonHalo")
local aura = tool:WaitForChild("MoonAura")
local haloWeld = halo:WaitForChild("HaloWeld")
local light = blade:WaitForChild("MoonLight")
local burst = blade:WaitForChild("MoonBurst")
local trails = { blade:WaitForChild("SlashTrail"), blade:WaitForChild("SlashCore") }

local DAMAGE = 18
local COOLDOWN = 0.55
local SWING_TIME = 0.4
local NINTH_MOON_MULTIPLIER = 3 -- every ninth hit is empowered
local HALO_SPEED = 1.4 -- radians per second
local HALO_SWING_BOOST = 6

local MOON = Color3.fromRGB(178, 235, 255)

local swinging = false
local lastSwing = 0
local hits = 0
local struck = {}

-- slow breathing glow on every moon
local pulse = TweenInfo.new(1.6, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true)
for _, name in { "Moons", "MoonOrbs", "CrownGem", "Vein", "MoonHalo" } do
	local part = tool:FindFirstChild(name)
	if part then
		TweenService:Create(part, pulse, { Color = part.Color:Lerp(Color3.new(1, 1, 1), 0.6) }):Play()
	end
end
TweenService:Create(aura, pulse, { Transparency = 0.8 }):Play()

-- the halo of nine moons orbits the blade while the sword is held
local haloBase = haloWeld.C0
local haloAxis = halo:GetAttribute("SpinAxis") or Vector3.yAxis
local haloAngle = 0
local spin

local function setTrails(enabled)
	for _, trail in trails do
		trail.Enabled = enabled
	end
end

local function flash(brightness)
	light.Brightness = brightness
	TweenService:Create(light, TweenInfo.new(0.5), { Brightness = 1.5 }):Play()
end

local function shockwave(position)
	local wave = Instance.new("Part")
	wave.Shape = Enum.PartType.Ball
	wave.Material = Enum.Material.Neon
	wave.Color = MOON
	wave.Transparency = 0.35
	wave.Size = Vector3.one
	wave.Anchored = true
	wave.CanCollide = false
	wave.CanQuery = false
	wave.CanTouch = false
	wave.CastShadow = false
	wave.Position = position
	wave.Parent = workspace
	TweenService:Create(wave, TweenInfo.new(0.45, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
		Size = Vector3.one * 16,
		Transparency = 1,
	}):Play()
	Debris:AddItem(wave, 0.6)
end

tool.Equipped:Connect(function()
	burst:Emit(45)
	flash(5)
	spin = RunService.Heartbeat:Connect(function(dt)
		haloAngle += dt * HALO_SPEED * (swinging and HALO_SWING_BOOST or 1)
		haloWeld.C0 = haloBase * CFrame.fromAxisAngle(haloAxis, haloAngle)
	end)
end)

tool.Activated:Connect(function()
	local now = os.clock()
	if now - lastSwing < COOLDOWN then
		return
	end
	lastSwing = now

	-- the default Animate script plays the slash when this value appears
	local anim = Instance.new("StringValue")
	anim.Name = "toolanim"
	anim.Value = "Slash"
	anim.Parent = tool

	table.clear(struck)
	swinging = true
	setTrails(true)
	flash(3.5)
	task.delay(SWING_TIME, function()
		if lastSwing == now then
			swinging = false
			setTrails(false)
		end
	end)
end)

blade.Touched:Connect(function(hit)
	if not swinging then
		return
	end
	local victim = hit:FindFirstAncestorOfClass("Model")
	if not victim or victim == tool.Parent then
		return
	end
	local humanoid = victim:FindFirstChildOfClass("Humanoid")
	if not humanoid or humanoid.Health <= 0 or struck[humanoid] then
		return
	end
	struck[humanoid] = true

	hits += 1
	local damage = DAMAGE
	if hits % 9 == 0 then
		damage *= NINTH_MOON_MULTIPLIER
		burst:Emit(110)
		flash(8)
		shockwave(hit.Position)
	else
		burst:Emit(20)
	end
	humanoid:TakeDamage(damage)
end)

tool.Unequipped:Connect(function()
	swinging = false
	setTrails(false)
	if spin then
		spin:Disconnect()
		spin = nil
	end
end)
]==]
combat.Parent = tool

tool.Parent = game:GetService("StarterPack")
if model.Parent and #model:GetDescendants() == 0 then
	model:Destroy()
end
Selection:Set({ tool })
print("King of the Nine Moons is ready in StarterPack")

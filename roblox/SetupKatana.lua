--[[
	King of the Nine Moons - one-shot setup for Roblox Studio.

	1. File > Import 3D > models/KingOfTheNineMoons.obj
	   (turn OFF "Import as single mesh", scale unit = Stud).
	2. Select the imported model in the Explorer.
	3. Paste this whole file into the Command Bar (View > Command Bar) and press Enter.

	The model is converted into a ready-to-use Tool in StarterPack with materials,
	glow, particles, a slash trail and a combat script.
]]

local Selection = game:GetService("Selection")

local model = Selection:Get()[1]
assert(model and (model:IsA("Model") or model:IsA("Folder")), "Select the imported katana model first")

local GOLD = Color3.fromRGB(242, 189, 66)
local MOON = Color3.fromRGB(178, 235, 255)

-- name = { color, material, reflectance }
local STYLE = {
	Blade = { Color3.fromRGB(26, 28, 46), Enum.Material.Metal, 0.35 },
	Hamon = { Color3.fromRGB(189, 214, 255), Enum.Material.Metal, 0.6 },
	Moons = { MOON, Enum.Material.Neon, 0 },
	Habaki = { GOLD, Enum.Material.Metal, 0.3 },
	Tsuba = { Color3.fromRGB(33, 28, 56), Enum.Material.Metal, 0.15 },
	GuardRim = { GOLD, Enum.Material.Metal, 0.3 },
	MoonOrbs = { MOON, Enum.Material.Neon, 0 },
	Fuchi = { GOLD, Enum.Material.Metal, 0.3 },
	Tsuka = { Color3.fromRGB(219, 219, 235), Enum.Material.Sand, 0 },
	Ito = { Color3.fromRGB(51, 26, 92), Enum.Material.Fabric, 0 },
	Kashira = { GOLD, Enum.Material.Metal, 0.3 },
	CrownGem = { Color3.fromRGB(184, 92, 255), Enum.Material.Neon, 0 },
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

for name, part in parts do
	local style = STYLE[name]
	part.Name = name
	part.Color = style[1]
	part.Material = style[2]
	part.Reflectance = style[3]
	part.Anchored = false
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = name == "Blade"
	part.Massless = true
	part.CastShadow = style[2] ~= Enum.Material.Neon
	part.Parent = tool

	local weld = Instance.new("WeldConstraint")
	weld.Part0 = handle
	weld.Part1 = part
	weld.Parent = part
end

local blade = parts.Blade
local size = blade.Size

-- Slash trail between the base of the blade and the tip (the tip curves towards -Z).
local base = Instance.new("Attachment")
base.Name = "TrailBase"
base.Position = Vector3.new(0, -size.Y * 0.42, 0)
base.Parent = blade

local tip = Instance.new("Attachment")
tip.Name = "TrailTip"
tip.Position = Vector3.new(0, size.Y * 0.5, -size.Z * 0.5 + 0.05)
tip.Parent = blade

local trail = Instance.new("Trail")
trail.Name = "SlashTrail"
trail.Attachment0 = base
trail.Attachment1 = tip
trail.Lifetime = 0.28
trail.MinLength = 0.05
trail.LightEmission = 1
trail.FaceCamera = false
trail.Color = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.new(1, 1, 1)),
	ColorSequenceKeypoint.new(0.4, MOON),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(120, 70, 255)),
})
trail.Transparency = NumberSequence.new({
	NumberSequenceKeypoint.new(0, 0.15),
	NumberSequenceKeypoint.new(1, 1),
})
trail.Enabled = false
trail.Parent = blade

local function moonDust(name, rate)
	local emitter = Instance.new("ParticleEmitter")
	emitter.Name = name
	emitter.Rate = rate
	emitter.Lifetime = NumberRange.new(0.7, 1.4)
	emitter.Speed = NumberRange.new(0.3, 1.2)
	emitter.SpreadAngle = Vector2.new(180, 180)
	emitter.Acceleration = Vector3.new(0, 1.5, 0)
	emitter.Rotation = NumberRange.new(0, 360)
	emitter.RotSpeed = NumberRange.new(-90, 90)
	emitter.LightEmission = 1
	emitter.Size = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.05),
		NumberSequenceKeypoint.new(0.3, 0.28),
		NumberSequenceKeypoint.new(1, 0),
	})
	emitter.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.2),
		NumberSequenceKeypoint.new(1, 1),
	})
	emitter.Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(150, 110, 255))
	emitter.Parent = blade
	return emitter
end

moonDust("MoonDust", 14)
local burst = moonDust("MoonBurst", 0)
burst.Speed = NumberRange.new(6, 14)
burst.Lifetime = NumberRange.new(0.3, 0.7)

local light = Instance.new("PointLight")
light.Name = "MoonLight"
light.Color = MOON
light.Brightness = 1.4
light.Range = 9
light.Parent = blade

local combat = Instance.new("Script")
combat.Name = "KatanaServer"
combat.Source = [==[
local TweenService = game:GetService("TweenService")

local tool = script.Parent
local blade = tool:WaitForChild("Blade")
local trail = blade:WaitForChild("SlashTrail")
local burst = blade:WaitForChild("MoonBurst")

local DAMAGE = 18
local COOLDOWN = 0.55
local SWING_TIME = 0.4
local NINTH_MOON_MULTIPLIER = 3 -- every ninth hit is empowered

local swinging = false
local lastSwing = 0
local hits = 0
local struck = {}

-- slow breathing glow on every moon
local pulse = TweenInfo.new(1.6, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true)
for _, name in { "Moons", "MoonOrbs", "CrownGem" } do
	local part = tool:FindFirstChild(name)
	if part then
		TweenService:Create(part, pulse, { Color = part.Color:Lerp(Color3.new(1, 1, 1), 0.65) }):Play()
	end
end

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
	trail.Enabled = true
	task.delay(SWING_TIME, function()
		if lastSwing == now then
			swinging = false
			trail.Enabled = false
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
		burst:Emit(90)
	else
		burst:Emit(18)
	end
	humanoid:TakeDamage(damage)
end)

tool.Unequipped:Connect(function()
	swinging = false
	trail.Enabled = false
end)
]==]
combat.Parent = tool

tool.Parent = game:GetService("StarterPack")
if model.Parent and #model:GetDescendants() == 0 then
	model:Destroy()
end
Selection:Set({ tool })
print("King of the Nine Moons is ready in StarterPack")

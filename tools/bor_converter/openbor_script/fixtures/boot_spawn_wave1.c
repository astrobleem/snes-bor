void boot_spawn_wave1()
{
   //Synthetic entry-point script for plan_vm.md's Task #13 (shipping a real
   //compiled openborscript module through the normal MSU/Vm_Load path,
   //replacing the Gate 0 test fixture that has shipped there since Gate 0a).
   //
   //NOT extracted from a mod pak -- this project's real target scripts
   //(SPAWN000.C-shaped subroutines with parameters) can't be an entry_main
   //by themselves yet: compiler.py's compile_program() takes zero args for
   //entry_main (no CALL/PARAM frame is synthesized for a real caller), and
   //the compiler has no codegen for a script-to-script CALL that WOULD
   //supply real arguments (compile_call only emits TARGET_KIND_NATIVE --
   //see natives.py's CALL_SPECIALIZATIONS; there is no TARGET_KIND_SCRIPT
   //path from a real .C source yet, only vm_gate3.py's hand-built synthetic
   //instruction streams exercise that opcode). This script inlines
   //SPAWN000.C's own body with fixed literal offsets instead of parameters,
   //using exactly the same 9 native calls (same natives.py specializations,
   //same stable IDs 100-108) already proven correct against real hardware
   //by vm_gate6.py -- it is content, not new VM/native surface.
   //
   //Effect: spawns one AI entity 40 world-X pixels ahead of the player,
   //at the player's own Y and facing, the first frame after boot.

   // iDirection is read but never used -- kept (rather than trimmed) so
   // this module exercises all 9 natives vm_gate6.py already proved
   // correct on real hardware (natives.py IDs 100-108), same as
   // SPAWN000.C itself calls. setspawnentry("name", 0) similarly passes
   // an inert integer where the real script passes a model-name string --
   // SETSPAWNENTRY_NAME ignores its argument entirely (see
   // vm_native_engine.pasm's header), so this is not roster selection.
   void self = getlocalvar("self");
   void vSpawn;
   int  iDirection = getentityproperty(self, "direction");

   clearspawnentry();
   setspawnentry("name", 0);

   float fX = getentityproperty(self, "x");
   float fY = getentityproperty(self, "a");
   float fZ = getentityproperty(self, "z");

   fX = fX + 40;

   vSpawn = spawn();

   changeentityproperty(vSpawn, "position", fX, fZ, fY);

   return vSpawn;
}

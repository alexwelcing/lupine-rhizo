import OpenDistillationFactory.DiscoveryChains.Chain01
import OpenDistillationFactory.DiscoveryChains.Chain02
import OpenDistillationFactory.DiscoveryChains.Chain03
import OpenDistillationFactory.DiscoveryChains.Chain04
import OpenDistillationFactory.DiscoveryChains.Chain05
import OpenDistillationFactory.DiscoveryChains.Chain06
import OpenDistillationFactory.DiscoveryChains.Chain07
import OpenDistillationFactory.DiscoveryChains.Chain08
import OpenDistillationFactory.DiscoveryChains.Chain09
import OpenDistillationFactory.DiscoveryChains.Chain10
import OpenDistillationFactory.DiscoveryChains.Chain11

/-! Chapter 15 discovery-chain contract suite. -/

namespace OpenDistillationFactory.DiscoveryChains

/-- Canonical portfolio order from Chapter 15. -/
def allContracts : List ChainContract :=
  [Chain01.contract, Chain02.contract, Chain03.contract, Chain04.contract,
   Chain05.contract, Chain06.contract, Chain07.contract, Chain08.contract,
   Chain09.contract, Chain10.contract, Chain11.contract]

theorem all_contracts_count : allContracts.length = 11 := by decide

theorem all_contracts_valid : ∀ contract ∈ allContracts, ContractValid contract := by
  intro contract hmem
  simp [allContracts] at hmem
  rcases hmem with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl
  all_goals first
    | exact Chain01.contract_valid
    | exact Chain02.contract_valid
    | exact Chain03.contract_valid
    | exact Chain04.contract_valid
    | exact Chain05.contract_valid
    | exact Chain06.contract_valid
    | exact Chain07.contract_valid
    | exact Chain08.contract_valid
    | exact Chain09.contract_valid
    | exact Chain10.contract_valid
    | exact Chain11.contract_valid

end OpenDistillationFactory.DiscoveryChains

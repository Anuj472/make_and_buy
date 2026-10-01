# Make or Buy Optimization Model: Database Schema

This document outlines the data structure required to build the Make or Buy optimization model described in the research paper. The schema is organized into five primary tables to handle global parameters, designs, components, in-house capabilities, and supplier data.

## 1. Orders (Global Parameters)
This table holds the overarching details and constraints for a specific customer order.

| Attribute | Notation | Description | Data Type |
| :--- | :--- | :--- | :--- |
| `Order_ID` | - | Unique identifier for the customer order (Primary Key). | Integer/UUID |
| `Demand_Quantity` | $w_o$ | Total number of final products required. | Integer |
| `Due_Date_Minutes` | $w_o$ | The deadline converted into minutes. | Float |
| `Tardiness_Cost_Per_Minute` | $Cl$ | Penalty cost for every minute past the due date. | Float (Currency) |
| `Quality_Loss_Coefficient` | $A_p$ | Monetary value assigned to product deviation. | Float (Currency) |
| `Final_Product_Tolerance` | $T_{Ah}^2$ | The allowable tolerance limit for the finished product. | Float |

## 2. Product_Designs
The model allows choosing between different overall product designs. This table stores costs and times associated with assembling a specific design.

| Attribute | Notation | Description | Data Type |
| :--- | :--- | :--- | :--- |
| `Design_ID` | $h$ | Unique identifier for the product design (Primary Key). | Integer |
| `Design_Name` | - | Human-readable name for the design. | String |
| `Design_Phase_Cost` | $cd_h$ | Fixed cost to develop this design. | Float (Currency) |
| `Design_Phase_Time` | $wd_h$ | Time taken to finalize the design. | Float (Minutes) |
| `Assembly_Cost` | $ca_h$ | Cost to assemble this specific design per unit. | Float (Currency) |
| `Assembly_Time` | $wa_h$ | Time taken to assemble this design per unit. | Float (Minutes) |
| `Assembly_Variance` | $\sigma_{Ah}^2$ | Inherent variance introduced during assembly. | Float |

## 3. Components
Represents the sub-parts required for each design.

| Attribute | Notation | Description | Data Type |
| :--- | :--- | :--- | :--- |
| `Component_ID` | $i$ | Unique identifier for the component (Primary Key). | Integer |
| `Design_ID` | $h$ | Links back to the `Product_Designs` table (Foreign Key). | Integer |
| `Component_Name` | - | Human-readable name (e.g., "Revolution Axis"). | String |

## 4. InHouse_Manufacturing (The "Make" Data)
Stores the metrics for every possible internal step. A component goes through multiple phases, and each phase might have alternative machines/processes.

| Attribute | Notation | Description | Data Type |
| :--- | :--- | :--- | :--- |
| `InHouse_Process_ID` | - | Unique identifier for this specific routing step (Primary Key). | Integer |
| `Component_ID` | $i$ | Links back to the `Components` table (Foreign Key). | Integer |
| `Phase_Number` | $j$ | The routing sequence (e.g., Phase 1, Phase 2). | Integer |
| `Alternative_Process_ID` | $k$ | Identifier for the specific machine/process alternative. | Integer |
| `Unit_Manufacturing_Cost` | $cm_{hijk}$ | Cost to process one unit on this machine. | Float (Currency) |
| `Processing_Time` | $wp_{hijk}$ | Minutes to process one unit. | Float (Minutes) |
| `Max_Capacity` | $K_{hijk}$ | Maximum number of units this machine can handle. | Integer |
| `Process_Variance` | $t_{hijk}$ | The quality variance (in mm) this machine produces. | Float |
| `Unit_Insp_Corr_Cost` | $ci_{hijk}$ | Cost to inspect and fix defects from this machine. | Float (Currency) |
| `Probability_of_Defect` | $\hat{P}_{hijk}$ | The non-conformance rate of this specific machine. | Float |

## 5. Suppliers (The "Buy" Data)
Acts as the catalog of available outsourcing options for each component.

| Attribute | Notation | Description | Data Type |
| :--- | :--- | :--- | :--- |
| `Supplier_ID` | $l$ | Unique identifier for the supplier (Primary Key). | Integer |
| `Component_ID` | $i$ | Links back to the `Components` table (Foreign Key). | Integer |
| `Supplier_Name` | - | Name of the supplier. | String |
| `Unit_Purchasing_Cost` | $cs_{hil}$ | Price to buy one unit of this component. | Float (Currency) |
| `Lead_Time` | $ws_{hil}$ | Processing/shipping time required per unit. | Float (Minutes) |
| `Max_Capacity` | $K_{hil}$ | Maximum units the supplier can provide for this order. | Integer |
| `Supplier_Variance` | $t_{hil}$ | The quality variance (in mm) guaranteed by the supplier. | Float |

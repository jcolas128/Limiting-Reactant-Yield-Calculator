######################################################################################################

"""
Joel Colas
Prof. Belford
CISC-106 Final Project

Limiting Reactant & Yield Calculator, a Drafter website

Enter a balanced equation and the mass of each reactant. The site finds the
limiting reactant, the theoretical yield of each product, and the percent
yield. It also has a molar mass lookup page
"""

from dataclasses import dataclass
from drafter import *

def load_molar_masses(filename: str) -> dict[str, float]:
    """
    Reads the datafile (lines like 'H,1.008') into a dictionary. Which
    that stores information in key-value pairs

    Args:
        str: filename, the name of the csv datafile to read

    Returns:
        dict[str, float]: element symbol -> molar mass in g/mol
    """
    masses: dict[str, float] = {}
    file = open(filename)
    for line in file:
        parts = line.strip().split(",")
        if len(parts) == 2 and parts[0] != "symbol":   
            masses[parts[0]] = float(parts[1])
    file.close()
    return masses

molar_masses = load_molar_masses("molar_masses.csv")

######################################################################################################

@dataclass
class Compound:
    """
    One reactant or product in the equation
    """
    formula: str # the chemical formula, like 'Ca(OH)2'
    coefficient: int # the number in front of it in the balanced equation
    molar_mass: float # grams per mole
    mass_grams: float # the mass the user entered, in grams (reactants only)
    moles: float # mass_grams / molar_mass

@dataclass
class State:
    """
    Everything the website needs to remember between pages
    """
    reactants: list[Compound] # the reactants the user has entered
    products: list[Compound] # the products the user has entered
    limiting_reactant: str # formula of the limiting reactant
    limiting_ratio: float # moles of the limiting reactant / its coefficient
    selected_product: str # formula of the product the user measured
    theoretical_yield: float # theoretical yield of the selected product, in grams
    percent_yield: float # the percent yield of the selected product
    message: str # an error or result message shown on the current page
    mass_index: int # which reactant's mass we are asking for right now

######################################################################################################
    
def is_number(text: str) -> bool:
    """
    Check whether text looks like a number such as '12' or '3.5'.
    Blanks, letters and negative numbers do not count

    Args:
        str: the text typed in by the user

    Returns:
        bool: True if text is a non-negative number, otherwise False
    """
    return text.replace(".", "", 1).isdigit()

def read_number(text: str, i: int) -> tuple[int, int]:
    """
    Read the digits that start at position i. If there are no digits,
    the number is 1

    Args:
        str: the text to read from
        int: the position in text to start reading at

    Returns:
        int: the number that was read
        int: the position in text just after the digits
    """
    digits = ""
    while i < len(text) and text[i].isdigit():
        digits += text[i]
        i += 1
    if digits == "":
        return (1, i)
    return (int(digits), i)

def compute_molar_mass(formula: str) -> float:
    """
    Find the molar mass of a formula like 'C6H12O6' or 'Ca(OH)2'

    Args:
        str: the chemical formula to read

    Returns:
        float: the molar mass in g/mol, or 0.0 if the formula can't be read
    """
    if formula == "":
        return 0.0
    total = 0.0
    group = 0.0          # running total for the part inside ( )
    in_group = False
    i = 0
    while i < len(formula):
        if formula[i] == "(":
            if in_group:
                return 0.0       # no parentheses inside parentheses
            in_group = True
            group = 0.0
            i += 1
        elif formula[i] == ")":
            if not in_group:
                return 0.0       # ")" with no "(" before it
            multiplier, i = read_number(formula, i + 1)
            if multiplier == 0:
                return 0.0
            total += group * multiplier
            in_group = False
        elif formula[i].isupper():
            # Element symbol: one capital letter followed by lowercase letters
            symbol = formula[i]
            i += 1
            while i < len(formula) and formula[i].islower():
                symbol += formula[i]
                i += 1
            count, i = read_number(formula, i)
            if symbol not in molar_masses or count == 0:
                return 0.0
            if in_group:
                group += molar_masses[symbol] * count
            else:
                total += molar_masses[symbol] * count
        else:
            return 0.0           # a character we don't understand
    if in_group:
        return 0.0               # "(" was never closed
    return total

def check_compound(formula: str, coefficient: str) -> str:
    """
    Check that a formula and a coefficient typed in by the user are valid

    Args:
        str: the chemical formula typed in
        str: the coefficient typed in

    Returns:
        str: an error message, or an empty string if both are fine
    """
    if compute_molar_mass(formula.strip()) == 0.0:
        return "Couldn't read that formula. Use element symbols, numbers and parentheses, like H2O or Ca(OH)2."
    if not coefficient.strip().isdigit() or int(coefficient) < 1:
        return "Coefficient must be a whole number of 1 or more."
    return ""


def make_compound(formula: str, coefficient: str) -> Compound:
    """
    Build a Compound from text that has already passed check_compound

    Args:
        str: the chemical formula typed in
        str: the coefficient typed in

    Returns:
        Compound: a new Compound with its molar mass filled in and a mass and moles of 0.0
    """
    formula = formula.strip()
    return Compound(formula, int(coefficient), compute_molar_mass(formula), 0.0, 0.0)


def equation_text(compounds: list[Compound]) -> str:
    """
    Turn a list of compounds into text like '2 H2  +  1 O2'

    Args:
        list[Compound]: compounds, the reactants or products to show

    Returns:
        str: the compounds with their coefficients, joined by plus signs
    """
    text = ""
    for compound in compounds:
        if text != "":
            text += "  +  "
        text += f"{compound.coefficient} {compound.formula}"
    return text


def to_grams(value: float, unit: str) -> float:
    """
    Convert a mass in g, mg or kg to grams

    Args:
        float: the mass as a number
        str: 'g', 'mg' or 'kg'

    Returns:
        float: the mass in grams
    """
    if unit == "mg":
        return value / 1000
    elif unit == "kg":
        return value * 1000
    return value


def find_limiting(state: State):
    """
    Find the limiting reactant (the one with the lowest moles / coefficient).
    Fills in each reactant's moles, plus the state's limiting_reactant and
    limiting_ratio

    Args:
        State: the current state, with every reactant's mass entered

    Returns:
        None: nothing is returned
    """
    lowest = -1.0  
    for reactant in state.reactants:
        reactant.moles = reactant.mass_grams / reactant.molar_mass
        ratio = reactant.moles / reactant.coefficient
        if lowest == -1.0 or ratio < lowest:
            lowest = ratio
            state.limiting_reactant = reactant.formula
    state.limiting_ratio = lowest


def theoretical_yield_of(state: State, product: Compound) -> float:
    """
    Find how much of a product we could make from the limiting reactant

    Args:
        State: the current state, after find_limiting has run
        Compound: the product to find the theoretical yield of

    Returns:
        float: the theoretical yield of the product, in grams
    """
    return state.limiting_ratio * product.coefficient * product.molar_mass


######################################################################################################

@route
def index(state: State) -> Page:
    """
    Home page: explains the site and has buttons to start or look up a molar mass

    Args:
        State: the current state

    Returns:
        Page: the home page
    """
    state.message = ""
    return Page(state, [
        Header("Limiting Reactant & Yield Calculator"),
        "Enter a balanced equation and your reactant masses to find the "
        "limiting reactant, theoretical yield, and percent yield.",
        LineBreak(),
        Button("Start", start_over),
        Button("Molar Mass Lookup", molar_mass_lookup),
    ])


@route
def start_over(state: State) -> Page:
    """
    Clear everything from the last calculation and begin a new one

    Args:
        State: the current state

    Returns:
        Page: the reactants page, with an empty equation
    """
    state.reactants = []
    state.products = []
    state.limiting_reactant = ""
    state.limiting_ratio = 0.0
    state.selected_product = ""
    state.theoretical_yield = 0.0
    state.percent_yield = 0.0
    state.message = ""
    state.mass_index = 0
    return enter_reactants(state)


@route
def enter_reactants(state: State) -> Page:
    """
    Page where the user adds reactants one at a time

    Args:
        State: the current state

    Returns:
        Page: the reactants page, showing the reactants entered so far
    """
    return Page(state, [
        Header("Step 1: Reactants"),
        "Enter your reactants: " + equation_text(state.reactants),
        LineBreak(),
        "Formula (like H2O or Ca(OH)2):",
        TextBox("formula", ""),
        "Coefficient:",
        TextBox("coefficient", "1"),
        Button("Add Reactant", add_reactant),
        Button("Next", reactants_done),
        Button("Home", index),
        LineBreak(),
        state.message,
    ])


@route
def add_reactant(state: State, formula: str, coefficient: str) -> Page:
    """
    Check the typed-in reactant and add it to the state if it is valid

    Args:
        State: the current state
        str: the formula typed in
        str: the coefficient typed in

    Returns:
        Page: the reactants page, with an error message if the input was invalid
    """
    error = check_compound(formula, coefficient)
    if error != "":
        state.message = error
    else:
        state.reactants.append(make_compound(formula, coefficient))
        state.message = ""
    return enter_reactants(state)


@route
def reactants_done(state: State) -> Page:
    """
    Move on to the products page, as long as there is at least one reactant

    Args:
        State: the current state

    Returns:
        Page: the products page, or the reactants page with an error message
    """
    if len(state.reactants) == 0:
        state.message = "Add at least one reactant first."
        return enter_reactants(state)
    state.message = ""
    return enter_products(state)


@route
def enter_products(state: State) -> Page:
    """
    Page where the user adds products one at a time

    Args:
        State: the current state

    Returns:
        Page: the products page, showing the products entered so far
    """
    return Page(state, [
        Header("Step 2: Products"),
        "So far: " + equation_text(state.products),
        LineBreak(),
        "Formula (like H2O or Ca(OH)2):",
        TextBox("formula", ""),
        "Coefficient:",
        TextBox("coefficient", "1"),
        Button("Add Product", add_product),
        Button("Next", products_done),
        Button("Back", back_to_reactants),
        LineBreak(),
        state.message,
    ])


@route
def add_product(state: State, formula: str, coefficient: str) -> Page:
    """
    Check the typed-in product and add it to the state if it is valid

    Args:
        State: the current state
        str: the formula typed in
        str: the coefficient typed in

    Returns:
        Page: the products page, with an error message if the input was invalid
    """
    error = check_compound(formula, coefficient)
    if error != "":
        state.message = error
    else:
        state.products.append(make_compound(formula, coefficient))
        state.message = ""
    return enter_products(state)


@route
def products_done(state: State) -> Page:
    """
    Move on to the masses page, as long as there is at least one product

    Args:
        State: the current state

    Returns:
        Page: the masses page, or the products page with an error message
    """
    if len(state.products) == 0:
        state.message = "Add at least one product first."
        return enter_products(state)
    state.message = ""
    state.mass_index = 0
    return enter_masses(state)


@route
def enter_masses(state: State) -> Page:
    """
    Page that asks for one reactant's mass at a time.
    state.mass_index says which reactant it is asking about

    Args:
        State: the current state

    Returns:
        Page: the masses page for the current reactant
    """
    reactant = state.reactants[state.mass_index]
    return Page(state, [
        Header("Step 3: Masses"),
        f"Mass of {reactant.formula} "
        f"({state.mass_index + 1} of {len(state.reactants)}):",
        TextBox("mass", ""),
        SelectBox("unit", ["g", "mg", "kg"], "g"),
        Button("Next", save_mass),
        Button("Back", back_to_products),
        LineBreak(),
        state.message,
    ])


@route
def save_mass(state: State, mass: str, unit: str) -> Page:
    """
    Check the typed-in mass, convert it to grams and save it on the current
    reactant. After the last reactant, find the limiting reactant

    Args:
        State: the current state
        str: the mass typed in
        str: the unit chosen: 'g', 'mg' or 'kg'

    Returns:
        Page: the next masses page, the results page after the last mass,
            or the same masses page with an error message
    """
    if not is_number(mass):
        state.message = "Mass must be a positive number."
        return enter_masses(state)
    value = float(mass)
    if value <= 0:
        state.message = "Mass must be greater than zero."
        return enter_masses(state)

    value = to_grams(value, unit)

    state.reactants[state.mass_index].mass_grams = value
    state.message = ""
    state.mass_index += 1
    if state.mass_index < len(state.reactants):
        return enter_masses(state)
    find_limiting(state)
    return results(state)


@route
def back_to_reactants(state: State) -> Page:
    """
    Go back from the products page to the reactants page

    Args:
        State: the current state

    Returns:
        Page: the reactants page, with any old error message cleared
    """
    state.message = ""
    return enter_reactants(state)


@route
def back_to_products(state: State) -> Page:
    """
    Go back from the masses page to the products page

    Args:
        State: the current state

    Returns:
        Page: the products page, with any old error message cleared
    """
    state.message = ""
    return enter_products(state)


@route
def results(state: State) -> Page:
    """
    Show each reactant's moles, the limiting reactant and the theoretical
    yield of every product. The user picks a product and types in the actual
    yield here

    Args:
        State: the current state, after find_limiting has run

    Returns:
        Page: the results page
    """
    masses = ""
    for reactant in state.reactants:
        if masses != "":
            masses += ";   "
        masses += f"{reactant.formula}: {reactant.mass_grams:.4f} g = {reactant.moles:.4f} mol"
    yields = ""
    names: list[str] = []
    for product in state.products:
        names.append(product.formula)
        if yields != "":
            yields += ";   "
        yields += f"{product.formula}: {theoretical_yield_of(state, product):.4f} g"
    return Page(state, [
        Header("Results"),
        masses,
        LineBreak(),
        f"Limiting reactant: {state.limiting_reactant}",
        LineBreak(),
        "Theoretical yield:  " + yields,
        LineBreak(),
        "Which product did you measure?",
        SelectBox("product", names, names[0]),
        "Actual yield (what you really got):",
        TextBox("actual", ""),
        SelectBox("unit", ["g", "mg", "kg"], "g"),
        Button("Calculate Percent Yield", calculate_yield),
        Button("Start Over", start_over),
        LineBreak(),
        state.message,
    ])


@route
def calculate_yield(state: State, product: str, actual: str, unit: str) -> Page:
    """
    Check the typed-in actual yield and calculate the percent yield of the
    chosen product

    Args:
        State: the current state
        str: the formula of the product the user chose
        str: the actual yield typed in
        str: unit, the unit chosen: 'g', 'mg' or 'kg'

    Returns:
        Page: the percent yield page, or the results page with an error message
    """
    if not is_number(actual):
        state.message = "Actual yield must be a number (0 or more)."
        return results(state)
    actual_grams = to_grams(float(actual), unit)
    for compound in state.products:
        if compound.formula == product:
            state.selected_product = product
            state.theoretical_yield = theoretical_yield_of(state, compound)
    state.percent_yield = actual_grams / state.theoretical_yield * 100
    state.message = ""
    return yield_page(state)


@route
def yield_page(state: State) -> Page:
    """
    Show the theoretical yield and percent yield of the chosen product,
    with a warning if the percent yield is over 100

    Args:
        State: the current state, after calculate_yield has run

    Returns:
        Page: the percent yield page
    """
    warning = ""
    if state.percent_yield > 100:
        warning = ("Over 100%! Double-check your measurement. Extra mass is often "
                   "leftover water or impurities.")
    return Page(state, [
        Header("Percent Yield"),
        f"Theoretical yield of {state.selected_product}: {state.theoretical_yield:.4f} g",
        LineBreak(),
        f"Percent yield: {state.percent_yield:.2f}%",
        LineBreak(),
        warning,
        LineBreak(),
        Button("Back", results),
        Button("Start Over", start_over),
    ])


@route
def molar_mass_lookup(state: State) -> Page:
    """
    Page where the user types in a formula to find its molar mass

    Args:
        State: the current state

    Returns:
        Page: the lookup page, showing the last result or error message
    """
    return Page(state, [
        Header("Molar Mass Lookup"),
        "Formula (like Ca(OH)2):",
        TextBox("formula", ""),
        Button("Look Up", show_molar_mass),
        Button("Back", index),
        LineBreak(),
        state.message,
    ])


@route
def show_molar_mass(state: State, formula: str) -> Page:
    """
    Calculate the molar mass of the typed-in formula and show it.

    Args:
        State: the current state
        str: the formula typed in

    Returns:
        Page: the lookup page, with the molar mass or an error message
    """
    formula = formula.strip()
    mass = compute_molar_mass(formula)
    if mass == 0.0:
        state.message = "Couldn't read that formula. Use element symbols and numbers, like H2O."
    else:
        state.message = f"{formula}: {mass:.3f} g/mol"
    return molar_mass_lookup(state)


start_server(State([], [], "", 0.0, "", 0.0, 0.0, "", 0))


from pydantic import BaseModel

class CarProfile(BaseModel):

    model: str
    profile: str
    differentiator: str


class CarBriefings(BaseModel):
    profiles: list[CarProfile]


ASSISTANT_NAME = "Nevo"

TEST_USER_NAME = "Peter"

TEST_USER_PROFILE = f"""{TEST_USER_NAME} lives on the countryside with a family of five, and two dogs. 
The main use for the car {TEST_USER_NAME} is looking for is a dailys commute to the city, 
but he will also be driving the kids to school and to soccer practice. 
Safety is very important to {TEST_USER_NAME}, but he also likes a car to be fast."""

TEST_USER_NAME2 = "Maryanne"
TEST_USER_PROFILE2 = f"""{TEST_USER_NAME2} lives in the city, is 22 and single. 
The main use for the car {TEST_USER_NAME2} is to get to university in the week and out to festivals on the weekend
Low cost and fuel efficiency are most important to {TEST_USER_NAME2}."""

TEST_RECOMMENDATION_TEXT_1 = """
Given what you've shared, I have two Audi models in mind that could be just the right fit for you: the Audi A3 and the Audi Q3.
First, the Audi A3. This compact car is perfect for city living where parking can be tight. It still packs enough luxury and sporty performance to keep you smiling on those weekend outings. It's a comfortable choice with modern features, and its smaller size makes it easy to zip around town.
Then the Audi Q3, which is a subcompact luxury SUV, giving you a little more space and a higher driving position without being too big for the city. It's also stylish, equipped with tech you’d love, and provides a comfy ride whether you're cruising through town or hitting the road for a getaway. Plus, the quattro all-wheel drive is a nice touch for added control and fun driving dynamics.
Both options are about blending comfort with the agility needed for your city lifestyle and your love for speed. Let me know if you've got any questions or need more info!
"""

TEST_RECOMMENDATION_TEXT_2 = """
Given your needs and lifestyle, there're two Audi models that I think would suit you well. First up is the Audi A6. It's a fantastic family car offering plenty of space for your kids and the dogs, with enough comfort to make those school and soccer runs smooth and enjoyable. Plus, it delivers on your need for speed with its powerful engine options, and it comes loaded with advanced safety features, which is always a win for peace of mind.
The second car I'd recommend is the Audi Q3. It's an SUV, offering you the height and space that's super handy for family activities and countryside living. The Q3 also has all-wheel drive for those less-than-ideal weather days, keeping safety in check, and it's compact enough for city driving and parking, which will come in handy during your daily commutes. It's a perfect blend of luxury, space, and practicality. 
Let me know if you have any questions or if you'd like to know more about these models!
"""

car_briefings = CarBriefings(
    profiles=[
        CarProfile(
            model="Audi A3",
            profile="""The Audi A3 - Overview
The Audi A3 is a small family car, also known as a C-segment car or a compact car. It is available as a 5-door hatchback called Sportback and as a 4-door sedan or saloon.

The Audi A3 particularly caters to customer needs for a premium, yet compact and practical vehicle. It provides an entry point into the Audi brand, offering a blend of luxury and sporty driving dynamics in a smaller size. The A3 meets the needs of customers who desire a car that is stylish, comfortable for daily commutes and family use, and equipped with modern technology, all while being more affordable and easier to maneuver and park than larger luxury sedans. Its availability as a Sportback enhances practicality with a spacious hatchback design suitable for everyday needs, while the saloon version offers a more traditional sedan style. The A3 also offers fuel efficiency, especially with its mild hybrid system and plug-in hybrid options, appealing to those conscious about running costs.

Typical customers for the Audi A3 are individuals or small families who want a premium car experience in a compact form. These customers appreciate the Audi brand's reputation for quality, sophisticated design, and advanced technology but may not require or desire a larger, more expensive vehicle. They might be young professionals, urban dwellers, or small families who need a car that is versatile for city driving, commuting, and occasional longer trips. The A3's size is well-suited for navigating urban environments and parking in tight spaces, while still offering a refined interior and enjoyable driving experience expected from a luxury brand. The availability of features like user-friendly infotainment systems, comfortable seats, and driver assistance technologies further appeals to those seeking a modern and convenient driving experience.""",
            differentiator="""Someone needing more space, luxury, or performance might prefer another Audi model over the A3. For instance, those requiring more passenger and cargo space for larger families or frequent travel with multiple passengers would likely prefer the Audi A4 or larger models like the A6. The A4 offers a more spacious interior, particularly in the back seats, and a larger trunk, making it a more practical family car. Customers prioritizing ultimate luxury, chauffeur-driven comfort, and advanced features might look towards the Audi A8. For those seeking enhanced performance and sportier handling beyond the A3's capabilities, Audi S and RS models, or even larger sports sedans within the Audi range, would be more suitable, offering significantly more power and sport-tuned driving dynamics.  While the A3 provides a balance of sportiness and comfort, drivers wanting a more pronounced sporty character might consider the Audi S3 or RS3 variants, or even other sportier models in Audi's lineup like the TT coupe or SUVs like the Q3 or Q5 for a higher driving position and more rugged appeal""",
        ),
        CarProfile(
            model="Audi A6",
            profile="""The Audi A6 - Overview

**What type of car is the Audi A6?**

The Audi A6 is an **executive car**, also described as a **luxury sports sedan** and a **mid-size sedan**. It is manufactured by the German company Audi and has been in production since 1994. The A6 is currently in its fifth generation and is available as both a **saloon/sedan** and an **estate/wagon** (marketed as Avant).

*   **What customer needs does the Audi A6 cater to in particular? Please explain why.**

The Audi A6 particularly caters to customers who need a vehicle that combines **luxury, performance, technology, and practicality**.

*   **Luxury and Comfort:** The A6 offers a **refined and sophisticated interior** with high-quality materials, comfortable and supportive seats, and a quiet cabin, ensuring a luxurious driving experience. Features like ambient lighting, eight-way power front seats, and four-zone climate control enhance comfort.
*   **Advanced Technology:** The A6 is equipped with advanced technology and infotainment features such as Audi's MMI touch response control with a high-resolution touchscreen, Audi Virtual Cockpit, and available Bang & Olufsen 3D Premium Sound System. These features appeal to **tech-savvy customers** who value connectivity and modern conveniences.
*   **Performance and Driving Dynamics:** The A6 provides a balanced combination of performance and comfort. It offers powerful yet efficient engine options, including both four-cylinder and V6 engines, and features like the quattro all-wheel-drive system for enhanced traction and stability. This caters to customers who desire a vehicle that is both **powerful and comfortable to drive**.
*   **Practicality:**  While being a luxury sedan, the A6 also offers practicality, especially in its Avant (estate) version, which provides **spaciousness for families or those needing extra cargo space**.  The sedan version also offers generous space for both front and rear passengers.
*   **Safety:** The Audi A6 is equipped with advanced safety and driver-assistance features like adaptive cruise control, lane-keeping assist, and automatic emergency braking, meeting the needs of customers who prioritize **safety and security**.

In essence, the Audi A6 is designed to meet the needs of discerning buyers who want a vehicle that is not only luxurious and stylish but also technologically advanced, performs well, and is practical for everyday use.

*   **Who are typical customers for the Audi A6? Please explain why.**

Typical customers for the Audi A6 are **affluent urban dwellers**, often described as being from the **upper middle class or upper class**. They are generally **well-educated professionals and executives**, typically in the **30-50 age group** and in the midst of their careers. These customers are **tech-savvy, modern, and up-to-date**, valuing **style, class, performance, and rider safety**.

*   **Affluent:** The A6 is a luxury vehicle with a premium price, so typical customers are those with higher incomes who can afford luxury vehicles.
*   **Urban Dwellers:**  Marketing strategies suggest Audi targets \"new urban buyers\" and \"affluent urbanized users\", indicating a focus on city residents who appreciate luxury and style in an urban environment.
*   **Professionals/Executives:** These individuals often seek vehicles that reflect their professional success and status. The A6, as an executive car, fits this image.
*   **Tech-Savvy Millennials and Younger Buyers:** Audi has developed vehicles aimed at the millennial market, indicating they are targeting younger, tech-oriented buyers who appreciate advanced technology and connectivity in their cars.
*   **Value Quality and Innovation:** Audi customers are described as appreciating technologically advanced and innovative products, along with attractive design, high-caliber materials, and build quality. They are drawn to Audi's reputation for quality, reliability, and performance.
*   **Both Men and Women:** Audi's marketing targets both male and female buyers, suggesting the A6's appeal is not limited by gender but rather by lifestyle and values.

In summary, typical Audi A6 customers are successful individuals who value luxury, technology, performance, and style, and who seek a vehicle that reflects their status and meets their sophisticated needs in an urban setting.""",
            differentiator="""*   **Who would rather prefer another model by Audi? Please explain why.**

While the Audi A6 is a versatile luxury car, some customers might prefer other Audi models based on their specific needs and preferences:

*   **Audi A4 or A3:** Customers seeking a **more affordable luxury car** or a **smaller, more agile vehicle** for city driving might prefer the Audi A4 or A3. These models are positioned below the A6 in Audi's sedan lineup and offer a more accessible entry point into the luxury market.
*   **Audi A8:**  Those desiring the **utmost luxury, prestige, and space** within the Audi sedan range would likely prefer the Audi A8. The A8 is Audi's flagship sedan, offering even more 고급스러운 features, a larger size, and often more powerful engine options than the A6.
*   **Audi A7:**  Customers who prioritize **style and a more unique design** might choose the Audi A7. The A7 is a hatchback version that is often described as \"prettier\" and more practical than the A6 sedan, offering a sloping roofline and a sportier aesthetic.
*   **Audi Q series (Q3, Q5, Q7, Q8):**  Customers needing **more space and versatility**, or those who prefer a higher driving position and all-weather capability, might opt for an Audi SUV like the Q3, Q5, Q7, or Q8. These models offer more cargo space, higher ground clearance, and SUV characteristics, making them suitable for families or those with active lifestyles.
*   **Audi e-tron models (Q4 e-tron, Q6 e-tron, Q8 e-tron, e-tron GT):** Environmentally conscious customers or those interested in **electric vehicles** would prefer Audi's e-tron range. These models are fully electric, offering zero-emission driving and aligning with the growing trend towards sustainable transportation.
*   **Audi S or RS models (S3, S4, S6, RS6, etc.):**  Customers prioritizing **sportiness and high performance** might choose the S or RS versions of other Audi models. For example, someone wanting a sportier version of the A6 might consider the Audi S6. Alternatively, for extreme performance, they might look at models like the RS6 Avant or other RS series cars.

In essence, while the A6 is a well-rounded luxury executive car, Audi's extensive model range offers alternatives that cater to more specific needs and preferences regarding size, price, body style, luxury level, performance, and powertrain (including electric options).""",
        ),
        CarProfile(
            model="Audi Q3",
            profile="""The Audi Q3 - Overview

* **What type of car is the Audi Q3?**

The Audi Q3 is a **subcompact luxury SUV** (Sport Utility Vehicle). It is Audi's entry-level SUV, positioned below the Audi Q5 in terms of size and price. It features a hatchback design with four doors and five seats.

* **What customer needs does the Audi Q3 cater to in particular? Please explain why.**

The Audi Q3 particularly caters to customers who need a vehicle that balances **luxury, style, technology, comfort, and practicality** in a **compact size**, making it well-suited for urban environments.

Here's a breakdown of the needs it addresses and why:

*   **Compact Size & Maneuverability:**  The Q3's subcompact dimensions make it easy to navigate city streets and parking, which is ideal for urban dwellers.
*   **Luxury and Premium Feel:** As an Audi, the Q3 offers a high-quality interior with premium materials, a well-crafted cabin, and advanced technology, appealing to those seeking a luxury experience.
*   **Technology and Connectivity:** The Q3 is equipped with modern technology features like a digital instrument cluster, touchscreen infotainment system with smartphone integration (Apple CarPlay, Android Auto), and driver-assistance systems, attracting tech-savvy buyers.
*   **Versatility and Practicality:** Despite its compact size, the Q3 provides a versatile cargo space with foldable rear seats, making it suitable for various lifestyles, from daily errands to weekend trips. It offers a comfortable and spacious cabin for a small family.
*   **Comfortable Ride Quality:** The Q3 is designed to provide a smooth and comfortable ride, effectively absorbing road imperfections, which is important for daily driving.
*   **All-Weather Capability:**  The Audi Q3 comes standard with all-wheel drive (Quattro), providing confident handling and stability in various weather conditions, appealing to customers in regions with inclement weather.
*   **Brand Image and Status:**  Owning an Audi Q3 provides the prestige and image associated with the Audi brand, which is attractive to buyers who value brand recognition and status.
*   **Entry-Level Luxury Affordability:**  Compared to larger luxury SUVs, the Q3 is positioned as a more affordable entry point into the luxury SUV market, making it accessible to a broader range of customers, including young professionals.

* **Who are typical customers for the Audi Q3? Please explain why.**

Typical customers for the Audi Q3 are often **affluent urban dwellers**, **young professionals**, and potentially **small families** or couples who value **style, quality, technology, and practicality** in a **compact luxury SUV**.

Reasons for this target customer profile:

*   **Affluent Urban Dwellers:** These customers appreciate luxury and convenience and often live in cities where compact, maneuverable vehicles are advantageous. They value style and are willing to pay for premium features.
*   **Young Professionals:**  The Q3's entry-level luxury status and blend of style, performance, and technology appeal to young professionals who are starting to enter the luxury car market. They seek a vehicle that is both functional and reflects their upward mobility. Audi has specifically targeted millennials with digital marketing campaigns for the Q3.
*   **Small Families or Couples:** The Q3 offers enough space and versatility for small families or couples who need a practical vehicle for daily life but don't require the larger size of a mid-size SUV. The cargo space and flexible seating arrangements accommodate their needs for carrying passengers and belongings.
*   **Tech-Savvy Individuals:** The advanced technology features in the Audi Q3, such as digital displays and smartphone integration, attract buyers who appreciate and utilize modern technology in their vehicles.
*   **Style-Conscious Buyers:** The Q3's sleek and modern exterior design, along with Audi's signature styling elements, appeals to customers who prioritize aesthetics and want a vehicle that looks stylish and upscale.
*   **Eco-Conscious Consumers:** Audi's focus on sustainability can also attract environmentally conscious buyers who seek luxury vehicles with some consideration for eco-friendly values.
""",
            differentiator="""* **Who would rather prefer another model by Audi? Please explain why.**

Customers who prioritize different needs might prefer another Audi model over the Q3:

*   **Families needing more space:**  Families requiring more passenger and cargo space would likely prefer the **Audi Q5** or **Audi Q7**. The Q5 offers more rear legroom and significantly more cargo capacity than the Q3, making it better suited for larger families or those who frequently haul more gear.
*   **Customers prioritizing ultimate luxury and refinement:** Those seeking a more luxurious and spacious interior, along with a more prestigious image within the Audi lineup, might opt for the **Audi Q5**, **Q7**, or even **Q8**. These larger SUVs offer more opulent interiors, enhanced comfort features, and a greater sense of luxury compared to the entry-level Q3. Alternatively, for sedan lovers, the **Audi A6** or **A8** would provide a step up in luxury and refinement.
*   **Enthusiasts seeking sportier driving dynamics:** While the Q3 offers agile handling, customers who prioritize a more engaging and sporty driving experience might prefer models like the **BMW X1** or even a sportier Audi sedan or coupe like the **Audi A4** or **A5**.  The BMW X1, for example, is often cited as offering sportier handling compared to the Q3.
*   **Buyers on a tighter budget:**  While the Q3 is Audi's entry-level SUV, it is still a luxury vehicle with a premium price. Customers looking for a more budget-friendly option, even within the Volkswagen group, might consider the **Volkswagen Tiguan**. The Tiguan offers similar practicality and space to the Q3, but at a lower price point, although it may lack the same level of luxury features and brand prestige. Alternatively, within Audi's range, someone strictly budget-conscious might consider a used, older Audi model.
*   **Customers wanting better fuel economy:** While the Q3 offers reasonable fuel efficiency for a luxury SUV, some buyers might prioritize even better fuel economy and consider hybrid or electric models like the **Audi Q4 e-tron** (electric SUV) or other hybrid SUVs in the market.  The Q3's fuel economy is sometimes considered \"subpar\" compared to some competitors.
*   **Customers who dislike SUVs:** Some buyers may simply prefer a sedan or wagon body style over an SUV. For these customers, Audi offers models like the **A4** or **A4 Avant (wagon)** which provide similar levels of luxury and practicality (especially the Avant) but in a different vehicle format. The A4 Avant can offer comparable cargo space to the Q3 with potentially more legroom.
*   **Customers wanting a more rugged or off-road focused SUV:** Although the Q3 has all-wheel drive, it is primarily designed for on-road use.  Those seeking a more rugged SUV with better off-road capabilities would need to look at brands specializing in off-road vehicles, as Audi's Q range is more focused on luxury and on-road performance.

In summary, the Audi Q3 is a strong choice for those seeking a compact luxury SUV that balances many desirable attributes. However, depending on individual priorities like space, luxury, sportiness, budget, or fuel economy, other Audi models or competitor vehicles might be a better fit.""",
        ),
        CarProfile(
            model="Audi A1",
            profile="""The Audi A1 – Overview

*   The Audi A1 is a **luxury supermini car** or a **premium quality small car**. It is available as a **luxurious hatchback** in three-door and five-door (Sportback) body styles.

*   The Audi A1 particularly caters to customer needs for a **stylish, well-built, and fun-to-drive vehicle** in the **compact car segment**. It addresses the need for a **premium badge** in a smaller size, appealing to those who want to experience luxury in a car suited for **everyday use**, especially in **urban environments**. The A1 also offers a **broad choice of engines**, including smaller, economical options and more powerful ones for a nippier drive. It provides a premium brand experience in a smaller package, which can be seen as an entry point into the luxury car market, especially for those new to the Audi brand. The availability of features like **Apple CarPlay and Android Auto** even in the base models, and optional packs for technology, comfort, and design, further enhance its appeal by catering to modern drivers' connectivity and personalization preferences.

*   Typical customers for the Audi A1 are often **younger individuals and couples, particularly under 40**, who are new to the Audi brand. These customers are often **urban dwellers**, including **young professionals and working women**, who desire a **premium city car** that is **elegant, well-designed, and compact**, with a **high-quality finish**. The A1 serves as an attractive 'first Audi' for those seeking to enter the luxury car market, offering prestige and brand recognition in a smaller, more manageable size. It appeals to customers who are **trading up from mainstream runabouts** and are willing to pay more for a premium experience in the supermini segment.
""",
            differentiator="""*   Customers who need **more space and practicality** would likely prefer another Audi model. For instance, someone needing more passenger room or cargo capacity might find the A3, A4, or even Audi SUVs like the Q3 or Q5 more suitable.  For those prioritizing performance, models like the S3 or S4 would be more appealing as they offer sportier engines and handling.  Individuals seeking ultimate luxury and advanced technology within the Audi range would likely prefer models like the A6 or A8, which are positioned in higher segments and offer more sophisticated features and larger dimensions.  While the A1 provides a premium experience in a compact size, it is inherently limited in space and outright performance compared to larger and more powerful models in the Audi lineup.""",
        ),
        CarProfile(
            model="Audi Q6",
            profile="""The Audi Q6 - Overview
    
The Audi Q6 is available in two distinct versions:

*   **Audi Q6 e-tron:** This is a **battery electric compact luxury crossover SUV**. It is part of Audi's shift towards electric vehicles and is intended to eventually replace the Audi Q5. The Q6 e-tron shares its platform with the Porsche Macan.
*   **Audi Q6 (China market):** This is a **full-size luxury crossover SUV with three-row seating**, produced in China through a joint venture. It is larger than the Q7 and Q8 in exterior dimensions and is built on the Volkswagen Group MQB Evo platform, sharing similarities with the Volkswagen Talagon and Atlas.  It is **not related to the Q6 e-tron** in terms of mechanics.

Considering the search results are primarily focused on the newer **Audi Q6 e-tron**, the following answers will mainly address this model unless specified otherwise.

The Audi Q6 e-tron particularly caters to customer needs for:

*   **Electric mobility:** As a fully electric SUV, it addresses the increasing demand for zero-emission vehicles and aligns with Audi's goal of transitioning to an all-electric fleet. This is for customers who are environmentally conscious and want to reduce their carbon footprint.
*   **Long range and fast charging:** The Q6 e-tron offers an EPA-estimated range of up to 321 miles with the Ultra package, alleviating range anxiety. Its 260kW DC fast-charging capability allows for quick battery top-ups (10-80% charge in a short time), catering to customers who need convenience and efficiency in charging.
*   **Spaciousness and practicality:**  Being a mid-size SUV, the Q6 e-tron provides ample space for passengers and luggage, meeting the practical needs of families or individuals who require versatility for daily use and longer trips. It offers considerable legroom in the second row and a usable cargo space.
*   **Luxury and technology:** The Q6 e-tron delivers a premium experience with a posh interior, cutting-edge technology, and a focus on user-centric design.  Features like the panoramic display, advanced infotainment system, and optional Bang & Olufsen sound system cater to customers seeking a sophisticated and technologically advanced vehicle.
*   **Performance and driving dynamics:**  Available in both rear-wheel drive and quattro all-wheel drive versions, including a high-performance SQ6 e-tron variant, the Q6 e-tron provides a range of power options.  The adaptive air suspension (standard on Prestige trim) further enhances the driving experience by adjusting ride height and damping for optimal comfort and handling.

Typical customers for the Audi Q6 e-tron are likely to be:

*   **Affluent urban dwellers:**  Audi's target market generally includes affluent city residents who value style, quality, and performance. These customers often appreciate luxury and cutting-edge technology.
*   **Tech-savvy individuals:**  The Q6 e-tron, with its advanced digital cockpit and infotainment system, appeals to tech-oriented buyers, including millennials, who appreciate seamless connectivity and innovative features.
*   **Eco-conscious consumers:** Individuals who are concerned about environmental impact and are looking to switch to electric vehicles will find the Q6 e-tron appealing due to its zero-emission powertrain and sustainable focus.
*   **Families or individuals needing a versatile SUV:**  Customers who require the space and practicality of an SUV for daily family needs, commutes, and longer journeys will be attracted to the Q6 e-tron's spacious interior and cargo capacity.
*   **Audi brand enthusiasts:**  Loyal Audi customers who appreciate the brand's reputation for quality, engineering, and sophisticated design are likely to consider the Q6 e-tron as their next vehicle, especially as they transition to electric mobility.

""",
            differentiator="""Individuals who might prefer another Audi model instead of the Q6 e-tron could include:

*   **Customers needing three-row seating:** For larger families or those who frequently need to transport more than five passengers, the China-market Audi Q6 with its three rows would be a more suitable choice.  However, if considering models available outside of China, the Audi Q7 or Q8, which offer three-row configurations, would be alternatives.
*   **Buyers prioritizing a smaller, more affordable electric SUV:**  Those looking for a slightly smaller and potentially more budget-friendly electric SUV within the Audi range might consider the Audi Q4 e-tron. While the Q6 e-tron is positioned between the Q4 and Q8 e-tron in size and price, the Q4 e-tron could be a better fit for those with tighter budgets or who prefer a more compact vehicle.
*   **Customers wanting a traditional combustion engine:**  Despite Audi's push towards electrification, some customers may still prefer vehicles with traditional internal combustion engines. For these buyers, the Audi Q5, which the Q6 e-tron is intended to supersede in the long run, or the larger Q7 and Q8 with their gasoline engine options, would remain relevant choices.  Audi continues to offer ICE, PHEV, and BEV options to cater to diverse customer preferences.
*   **Buyers seeking a sportier, coupe-like SUV EV:** Customers drawn to a more aggressively styled, coupe-inspired electric SUV might find the Audi Q6 Sportback e-tron more appealing. It offers a sportier silhouette compared to the standard Q6 e-tron SUV while retaining similar features and technology.
*   **Customers prioritizing ultimate luxury and larger size in an EV SUV:**  For those seeking the most luxurious and largest electric SUV in Audi's lineup, the Audi Q8 e-tron would be the preferred model. It sits above the Q6 e-tron in the hierarchy, offering enhanced luxury, potentially more space, and top-of-the-line features.",
""",
        ),
    ],
)


def get_car_briefings():
    output = [
        f"{profile.profile}\n\n{profile.differentiator}"
        for profile in sorted(car_briefings.profiles, key=lambda x: x.model)
    ]
    return "\n\n========\n\n".join(output)


def get_car_briefings_without_differentiators():
    output = [f"{profile.profile}" for profile in sorted(car_briefings.profiles, key=lambda x: x.model)]
    return "\n\n========\n\n".join(output)


def get_briefings_without_differentiator(model_1: str, model_2: str):
    output = [
        f"{profile.profile}"
        for profile in sorted(car_briefings.profiles, key=lambda x: x.model)
        if profile.model in [model_1, model_2]
    ]
    assert len(output) == 2
    return "\n\n========\n\n".join(output)


if __name__ == "__main__":
    print(get_car_briefings_without_differentiators())

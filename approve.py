import asyncio

from workflows.client import approve_workflow


async def main():

    workflow_id = "aiops-526e8c82-75cd-4b06-9e8b-0aae569944df"
    

    decision = input(
        "Décision (approved/rejected) : "
    )


    await approve_workflow(
        workflow_id,
        decision,
    )

    print("Décision envoyée à Temporal.")


if __name__ == "__main__":
    asyncio.run(main())
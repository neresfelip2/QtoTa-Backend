from sqlalchemy import DDL

trigger_ddl = DDL("""
CREATE TRIGGER trg_offer_no_overlap
ON dbo.offer
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.offer o
          ON o.id_product      = i.id_product
         AND o.id_store_branch = i.id_store_branch
         AND o.id             <> i.id
         AND o.start_date    <= i.expiration
         AND o.expiration    >= i.start_date
    )
    BEGIN
        RAISERROR(
            'Erro: existe outra oferta para este produto/filial com período que se sobrepõe.',
            16, 1
        );
        ROLLBACK TRANSACTION;
        RETURN;
    END
END
""")
# ocp-baremetal-redfish-virtualbmc

BMC virtual compativel com redfish para deploy de baremetal ocp no vsphere

Este é um utilitário muito simples para simular uma iBMC com compatibilidade Redfish. Isto possibilita simular deploy de baremetal em um ambiente virtual (Com algumas interações manuais)

Aplicação criada com ajuda do CHATGPT e testada em OCP 4.18 + ACM 2.13

**ATENÇÃO**

* Esta aplicação não monta a ISO automaticamente na maquina virtual, devemos analisar os logs gerados pela aplicação para baixar a iso manualmente e inserir
* Existem muitos melhoramentos possíveis

*DICA*

Eu utilizo aquela configuração na VM para que ela vá para a BIOS na inicialização, isso dá o tempo necessário para a montagem manual da ISO após o comando de incialização da VM feito pela iBMC

## Arquivos

`redfish-virtual.py` O emulador em sí, só executar com python e o nome do arquivo

`vmware-power.sh` Utiliza o govc para desligar e ligar as VMs. O govc é um pré-requisito

`ocp-ztp-01.yaml`: Um arquivo de exemplo para criação de cluster OCP e nodes correspondentes, através do ACM.

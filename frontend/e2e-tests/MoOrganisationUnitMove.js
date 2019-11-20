import { Selector } from 'testcafe'
import { baseURL, setup, teardown } from './support';
import VueSelector from 'testcafe-vue-selectors'

let moment = require('moment')

fixture('MoOrganisationUnitMove')
  .before(setup)
  .after(teardown)
  .page(`${baseURL}/organisation/fa2e23c9-860a-4c90-bcc6-2c0721869a25`)

const dialog = Selector('#orgUnitMove')

const unitInput = dialog.find('input[data-vv-as="Angiv enhed"]')

const parentInput = dialog.find('.parentUnit input[data-vv-as="Angiv ny overenhed"]')

const fromInput = dialog.find('.moveDate input.form-control')

const tree = VueSelector('mo-tree-view')

const currentUnitName = Selector('.orgunit .orgunit-name').with({ visibilityCheck: true})

test('Workflow: move unit', async t => {
  let today = moment()

  await t
    .expect(currentUnitName.innerText)
    .eql('IT-Support')
    .expect(tree.find('.selected').exists)
    .ok()
    .expect(tree.getVue(({ computed }) => computed.contents))
    .eql([
      "> Lønorganisation",
      {
        "Overordnet Enhed": [
          "> Humanistisk fakultet",
          "Samfundsvidenskabelige fakultet",
          {
            "Skole og Børn": [
              "=+= IT-Support =+="
            ]
          },
          "Social og sundhed"
        ]
      }
    ])

    .hover('#mo-workflow', { offsetX: 10, offsetY: 90 })
    .click('.btn-unit-move')

    .expect(dialog.exists).ok('Opened dialog')

    .click(unitInput)
    .click(dialog.find('.currentUnit .tree-content')
       .withText('Overordnet Enhed').find('.tree-arrow'))
    .click(dialog.find('.currentUnit .tree-content')
      .withText('Skole og Børn').find('.tree-arrow'))
    .click(dialog.find('.currentUnit .tree-anchor')
      .withText('IT-Support'))
    .expect(dialog.find('.currentUnit input[data-vv-as="Angiv enhed"]').value)
    .eql('IT-Support')

    .click(parentInput)
    .click(dialog.find('.parentUnit .tree-content')
      .withText('Overordnet Enhed')
      .find('.tree-arrow'))
    .click(dialog.find('.parentUnit .tree-anchor')
      .withText('Social og sundhed'))
    .expect(dialog.find('.parentUnit input[data-vv-as="Angiv ny overenhed"]').value)
    .eql('Social og sundhed')

    .click(fromInput)
    .hover(dialog.find('.vdp-datepicker .day:not(.blank)')
      .withText(today.date().toString()))
    .click(dialog.find('.vdp-datepicker .day:not(.blank)')
      .withText(today.date().toString()))
    .expect(fromInput.value).eql(today.format('DD-MM-YYYY'))

    .click(dialog.find('.btn-primary'))

    .expect(dialog.exists).notOk()

    .expect(VueSelector('MoLog')
      .find('.alert').nth(-1).innerText)
    .match(
      /Organisationsenheden med UUID [-0-9a-f]* er blevet flyttet/
    )

    .expect(tree.find('.selected').exists)
    .ok()

  await t
    .expect(tree.getVue(({ computed }) => computed.contents))
    .eql([
      "> Lønorganisation",
      {
        "Overordnet Enhed": [
          "> Humanistisk fakultet",
          "Samfundsvidenskabelige fakultet",
          "Skole og Børn",
          {
            "Social og sundhed": [
              "=+= IT-Support =+="
            ]
          }
        ]
      }
    ])
    .expect(Selector('.orgunit-name').textContent)
    .eql('IT-Support')
    .expect(Selector('.orgunit-location').textContent
           )
    .eql('Overordnet Enhed\\Social og sundhed')
    .expect(Selector('.detail-present .parent-name').textContent)
    .match(/Social og sundhed/)

    .click(Selector('.detail-past .card-header'))
    .expect(Selector('.detail-past .parent-name').textContent)
    .match(/Skole og Børn/)

    .click(Selector('.detail-future .card-header'))
    .expect(Selector('.detail-future .parent-name').exists).notOk()
})

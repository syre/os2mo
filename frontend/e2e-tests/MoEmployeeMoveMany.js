import { Selector } from 'testcafe'
import { baseURL } from './support'

let moment = require('moment')

fixture('Employee test')
  .page(`${baseURL}/medarbejder/liste`)

const dialog = Selector('#employeeMoveMany')

const fromInput = dialog.find('input.form-control')

const parentFromInput = dialog.find('.from-unit input[data-vv-as="Enhed"]')

const parentToInput = dialog.find('.to-unit input[data-vv-as="Enhed"]')

const checkboxInput = dialog.find('.checkbox-employee[data-vv-as="checkbox"]')

test('Workflow: moveMany employee', async t => {
  let today = moment()

  await t
    .setTestSpeed(0.8)
    .hover('#mo-workflow', {offsetX: 10, offsetY: 140})
    .click('.btn-employee-moveMany')

    .expect(dialog.exists).ok('Opened dialog')

    .click(fromInput)
    .hover(dialog.find('.vdp-datepicker .day:not(.blank)')
           .withText(today.date().toString()))
    .click(dialog.find('.vdp-datepicker .day:not(.blank)')
           .withText(today.date().toString()))
    .expect(fromInput.value).eql(today.format('DD-MM-YYYY'))

    .click(parentFromInput)
    .click(dialog.find('.from-unit li .item .link-color'))

    .click(parentToInput)
    .click(dialog.find('.to-unit li .item .link-color'))

    .click(checkboxInput)

    .click(dialog.find('.btn-primary'))

    .expect(Selector('#orgUnitRename').exists).notOk()
})
package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_8_2Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        String[] result = invokeValuesMethod(record);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] inputValues = {};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        String[] result = invokeValuesMethod(record);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] inputValues = {"singleValue"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        String[] result = invokeValuesMethod(record);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testGetMethod_validIndex() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        Assertions.assertEquals("value2", record.get(1));
    }

    @Test
    public void testGetMethod_invalidIndex() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> record.get(5));
    }

    @Test
    public void testIsConsistent() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        // Assuming isConsistent() returns true for valid records
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    public void testIsMapped() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("value1", 0);
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        Assertions.assertTrue(record.isMapped("value1"));
        Assertions.assertFalse(record.isMapped("value3"));
    }

    @Test
    public void testIsSet() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        Assertions.assertTrue(record.isSet("value1"));
        Assertions.assertFalse(record.isSet("value4"));
    }

    @Test
    public void testIterator() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
    }

    @Test
    public void testGetComment() throws Exception {
        String comment = "This is a comment";
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), comment, 1);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetRecordNumber() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 42);
        Assertions.assertEquals(42, record.getRecordNumber());
    }

    @Test
    public void testSize() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testToString() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        Assertions.assertEquals("CSVRecord{values=[value1, value2, value3], recordNumber=1}", record.toString());
    }

    private String[] invokeValuesMethod(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        return (String[]) method.invoke(record);
    }
}
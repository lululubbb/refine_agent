package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_8_1Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        String[] result = invokeValues(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] inputValues = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        String[] result = invokeValues(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] inputValues = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        String[] result = invokeValues(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testGetMethod() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testGetMethodOutOfBounds() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> record.get(3));
    }

    @Test
    public void testIsConsistent() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
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
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Assertions.assertFalse(record.isSet("value4"));
        mapping.put("value1", 0);
        Assertions.assertTrue(record.isSet("value1"));
    }

    @Test
    public void testIterator() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testGetComment() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, "This is a comment", 1);
        
        Assertions.assertEquals("This is a comment", record.getComment());
    }

    @Test
    public void testGetRecordNumber() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 5);
        
        Assertions.assertEquals(5, record.getRecordNumber());
    }

    @Test
    public void testSize() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testToString() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Assertions.assertEquals("CSVRecord{values=[value1, value2, value3]}", record.toString());
    }

    private String[] invokeValues(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        return (String[]) method.invoke(record);
    }
}
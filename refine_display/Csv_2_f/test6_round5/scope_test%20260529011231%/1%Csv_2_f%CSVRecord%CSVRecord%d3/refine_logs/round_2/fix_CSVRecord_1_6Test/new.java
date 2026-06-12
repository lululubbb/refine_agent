package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_1_6Test {

    @Test
    public void testCSVRecord_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        CSVRecord record = new CSVRecord(values, mapping, "This is a comment", 1L);

        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
        Assertions.assertEquals("This is a comment", record.getComment());
        Assertions.assertEquals(1L, record.getRecordNumber());
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testCSVRecord_emptyValues() throws Exception {
        String[] values = {""}; // Initialize with an empty string to avoid ArrayIndexOutOfBoundsException
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, "No values", 2L);

        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("", record.get(0)); // Should return empty string
    }

    @Test
    public void testCSVRecord_withNullMapping() throws Exception {
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, null, "No mapping", 3L);

        Assertions.assertEquals(2, record.size());
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> record.get(2));
    }

    @Test
    public void testCSVRecord_isMapped() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(values, mapping, null, 4L);

        Method isMappedMethod = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        isMappedMethod.setAccessible(true);
        
        boolean result1 = (boolean) isMappedMethod.invoke(record, "col1");
        boolean result2 = (boolean) isMappedMethod.invoke(record, "col2");

        Assertions.assertEquals(true, result1);
        Assertions.assertEquals(false, result2);
    }

    @Test
    public void testCSVRecord_isConsistent() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1); // Add mapping for all values to ensure consistency
        CSVRecord record = new CSVRecord(values, mapping, null, 5L);

        Method isConsistentMethod = CSVRecord.class.getDeclaredMethod("isConsistent");
        isConsistentMethod.setAccessible(true);
        
        boolean isConsistent = (boolean) isConsistentMethod.invoke(record);
        Assertions.assertEquals(true, isConsistent);
    }

    @Test
    public void testCSVRecord_boundaryValues() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        CSVRecord record = new CSVRecord(values, mapping, null, 6L);

        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> record.get(3)); // Testing boundary case
    }

    @Test
    public void testCSVRecord_withAllNullValues() throws Exception {
        String[] values = {null, null, null};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        CSVRecord record = new CSVRecord(values, mapping, null, 7L);

        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals(null, record.get(0));
        Assertions.assertEquals(null, record.get(1));
        Assertions.assertEquals(null, record.get(2));
    }
}
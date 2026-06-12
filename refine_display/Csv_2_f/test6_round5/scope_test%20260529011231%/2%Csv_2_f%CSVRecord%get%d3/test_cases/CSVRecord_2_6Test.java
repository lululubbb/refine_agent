package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_6Test {

    @Test
    public void testGet_validIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.get(1);
        
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(3);
        });
    }

    @Test
    public void testGet_negativeIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(-1);
        });
    }

    @Test
    public void testGet_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(0);
        });
    }

    @Test
    public void testGet_nullValue() throws Exception {
        String[] values = {null, "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.get(0);
        
        Assertions.assertEquals(null, result);
    }

    @Test
    public void testGet_emptyString() throws Exception {
        String[] values = {"", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.get(0);
        
        Assertions.assertEquals("", result);
    }

    @Test
    public void testGet_maxIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.get(2);
        
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testGet_boundaryValues() throws Exception {
        String[] values = {"first", "second", "third"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertEquals("first", record.get(0));
        Assertions.assertEquals("third", record.get(2));
    }

    private String[] getValues(CSVRecord record) throws Exception {
        java.lang.reflect.Field field = CSVRecord.class.getDeclaredField("values");
        field.setAccessible(true);
        return (String[]) field.get(record);
    }
}
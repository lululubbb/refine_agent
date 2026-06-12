package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_8_1Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(inputValues, mapping, comment, recordNumber);
        String[] result = invokeValues(record);

        Assertions.assertNotNull(result);
        Assertions.assertEquals(inputValues.length, result.length);
        for (int i = 0; i < inputValues.length; i++) {
            Assertions.assertEquals(inputValues[i], result[i]);
        }
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] inputValues = {};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 2;

        CSVRecord record = new CSVRecord(inputValues, mapping, comment, recordNumber);
        String[] result = invokeValues(record);

        Assertions.assertNotNull(result);
        Assertions.assertEquals(0, result.length);
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] inputValues = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Single value record";
        long recordNumber = 3;

        CSVRecord record = new CSVRecord(inputValues, mapping, comment, recordNumber);
        String[] result = invokeValues(record);

        Assertions.assertNotNull(result);
        Assertions.assertEquals(1, result.length);
        Assertions.assertEquals(inputValues[0], result[0]);
    }

    @Test
    public void testvalues_boundaryCase() throws Exception {
        String[] inputValues = {"first", "second"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("firstKey", 0);
        mapping.put("secondKey", 1);
        String comment = "Boundary case";
        long recordNumber = 4;

        CSVRecord record = new CSVRecord(inputValues, mapping, comment, recordNumber);
        String[] result = invokeValues(record);

        Assertions.assertNotNull(result);
        Assertions.assertEquals(inputValues.length, result.length);
        Assertions.assertEquals(inputValues[0], result[0]);
        Assertions.assertEquals(inputValues[1], result[1]);
    }

    @Test
    public void testvalues_nullValues() throws Exception {
        String[] inputValues = {"value1", null, "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        String comment = "Null value case";
        long recordNumber = 5;

        CSVRecord record = new CSVRecord(inputValues, mapping, comment, recordNumber);
        String[] result = invokeValues(record);

        Assertions.assertNotNull(result);
        Assertions.assertEquals(inputValues.length, result.length);
        Assertions.assertEquals(inputValues[0], result[0]);
        Assertions.assertNull(result[1]);
        Assertions.assertEquals(inputValues[2], result[2]);
    }

    private String[] invokeValues(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        return (String[]) method.invoke(record);
    }
}
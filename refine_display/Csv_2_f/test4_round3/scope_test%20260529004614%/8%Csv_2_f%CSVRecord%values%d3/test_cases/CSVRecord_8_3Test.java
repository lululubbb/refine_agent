package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_8_3Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValuesMethod(record);
        Assertions.assertEquals(Arrays.asList(inputValues), Arrays.asList(result));
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] inputValues = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValuesMethod(record);
        Assertions.assertEquals(Arrays.asList(inputValues), Arrays.asList(result));
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] inputValues = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValuesMethod(record);
        Assertions.assertEquals(Arrays.asList(inputValues), Arrays.asList(result));
    }

    @Test
    public void testvalues_nullMapping() throws Exception {
        String[] inputValues = {"value1", "value2"};
        CSVRecord record = new CSVRecord(inputValues, null, null, 1);

        String[] result = invokeValuesMethod(record);
        Assertions.assertEquals(Arrays.asList(inputValues), Arrays.asList(result));
    }

    @Test
    public void testvalues_boundaryCase() throws Exception {
        String[] inputValues = {null, "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValuesMethod(record);
        Assertions.assertEquals(Arrays.asList(inputValues), Arrays.asList(result));
    }

    private String[] invokeValuesMethod(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        return (String[]) method.invoke(record);
    }
}